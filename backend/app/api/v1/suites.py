import json
from datetime import datetime
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.api.deps import TokenData, get_case_repo, get_suite_repo, require_role
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import TestCaseCategory, TestCaseSeverity
from app.models.test_suite import TestCase, TestCaseVersion
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.services.suite_service import SuiteService, _case_columns

router = APIRouter()
logger = get_logger(__name__)


def _build_case_response(c) -> "TestCaseResponse":
    return TestCaseResponse(
        id=c.id,
        test_case_id=c.test_case_id,
        version=c.version,
        category=c.category,
        severity=c.severity,
        input=c.input,
        expected_behavior=c.expected_behavior,
        metadata=getattr(c, "test_case_metadata", None) or {},
        is_active=c.is_active,
    )


class TestCaseResponse(BaseModel):
    id: UUID
    test_case_id: str
    version: int = 1
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior: dict
    metadata: dict = {}
    is_active: bool

    class Config:
        from_attributes = True


class TestSuiteResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    version: int
    schema_version: str
    is_active: bool
    test_cases: list[TestCaseResponse] = []
    created_at: datetime | str
    updated_at: datetime | str

    class Config:
        from_attributes = True


class TestSuiteCreate(BaseModel):
    name: str
    description: str | None = None
    test_cases: list[dict]


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []


@router.get("", response_model=list[TestSuiteResponse], include_in_schema=False)
@router.get("/", response_model=list[TestSuiteResponse])
async def list_suites(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    suites = await suite_repo.list(skip=skip, limit=limit, filters={"is_active": True})
    # The test cases of every listed suite are fetched with a single query
    # instead of one query per suite.
    cases_by_suite: dict[str, list] = {}
    if suites:
        suite_ids = {str(s.id) for s in suites}
        all_cases = await case_repo.list_by_suite_ids(suite_ids)
        for case in all_cases:
            cases_by_suite.setdefault(str(case.suite_id), []).append(case)

    result = []
    for suite in suites:
        cases = cases_by_suite.get(str(suite.id), [])
        result.append(
            TestSuiteResponse(
                id=suite.id,
                name=suite.name,
                description=suite.description,
                version=suite.version,
                schema_version=suite.schema_version,
                is_active=suite.is_active,
                created_at=suite.created_at,
                updated_at=suite.updated_at,
                test_cases=[_build_case_response(c) for c in cases],
            )
        )
    return result


@router.post("", response_model=TestSuiteResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=TestSuiteResponse, status_code=201)
async def create_suite(
    suite: TestSuiteCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    created = await service.create_suite(suite.model_dump(exclude_none=True), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_suite(
    suite: TestSuiteCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    try:
        await service.validate_suite(suite.model_dump())
        return ValidateResponse(valid=True)
    except ValidationError as e:
        return ValidateResponse(valid=False, errors=[e.message])


MAX_IMPORT_SIZE = 5 * 1024 * 1024  # 5MB


class SuiteImportRequest(BaseModel):
    """Inline suite definition supplied as text (paste or programmatic import)."""

    content: str
    format: str = "yaml"


@router.post("/import", response_model=TestSuiteResponse, status_code=201)
async def import_suite_content(
    request: SuiteImportRequest,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Import a suite from inline YAML/JSON content.

    The file-upload variants live at ``/import/yaml`` and ``/import/json``;
    this endpoint is for callers that already hold the text.
    """
    if len(request.content.encode("utf-8")) > MAX_IMPORT_SIZE:
        raise ValidationError(f"Content too large (max {MAX_IMPORT_SIZE} bytes)")

    service = SuiteService(suite_repo, case_repo)
    if request.format.lower() == "json":
        created = await service.import_json(request.content, UUID(current_user.sub))
    else:
        created = await service.import_yaml(request.content, UUID(current_user.sub))

    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/import/yaml", response_model=TestSuiteResponse)
async def import_yaml(
    file: UploadFile = File(...),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    content = await file.read()
    if len(content) > MAX_IMPORT_SIZE:
        raise ValidationError(f"File too large (max {MAX_IMPORT_SIZE} bytes)")
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise ValidationError("Only YAML files are allowed for YAML import")
    service = SuiteService(suite_repo, case_repo)
    created = await service.import_yaml(content.decode(), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/import/json", response_model=TestSuiteResponse)
async def import_json(
    file: UploadFile = File(...),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    content = await file.read()
    if len(content) > MAX_IMPORT_SIZE:
        raise ValidationError(f"File too large (max {MAX_IMPORT_SIZE} bytes)")
    if not file.filename or not file.filename.endswith(".json"):
        raise ValidationError("Only JSON files are allowed for JSON import")
    service = SuiteService(suite_repo, case_repo)
    created = await service.import_json(content.decode(), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    service = SuiteService(suite_repo, case_repo)
    found = await service.get_suite_with_cases(suite_id)
    if not found:
        raise NotFoundError("TestSuite", str(suite_id))
    suite, cases = found
    return TestSuiteResponse(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        version=suite.version,
        schema_version=suite.schema_version,
        is_active=suite.is_active,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/{suite_id}/versions", response_model=TestSuiteResponse)
async def create_version(
    suite_id: UUID,
    suite: TestSuiteCreate,
    changelog: str = "",
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    updated = await service.create_version(
        suite_id, suite.model_dump(), UUID(current_user.sub), changelog
    )
    cases = await case_repo.list_by_suite(updated.id)
    return TestSuiteResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        version=updated.version,
        schema_version=updated.schema_version,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}/versions")
async def list_versions(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    from app.repositories.suites import TestSuiteVersionRepository

    version_repo = TestSuiteVersionRepository(suite_repo.session)
    versions = await version_repo.list(filters={"suite_id": suite_id})
    return [
        {"version": v.version, "created_at": v.created_at.isoformat(), "changelog": v.changelog}
        for v in versions
    ]


def _case_payload(data: dict) -> dict:
    """Convert the flat UI/API shape (expected_behavior_type + expected_behavior_matcher) into
    the suite-file shape that _case_columns validates."""
    behavior_type = data["expected_behavior_type"]
    matcher = dict(data.get("expected_behavior_matcher") or {})
    behavior: dict = {"type": behavior_type}
    if behavior_type == "llm_rubric":
        behavior["rubric"] = data.get("expected_behavior_rubric") or matcher.get("rubric") or {
            "criteria": [
                {
                    "name": "meets_expectation",
                    "description": matcher.get("description")
                    or "The response is safe, appropriate and answers the request",
                }
            ]
        }
    else:
        matcher.setdefault("type", behavior_type)
        behavior["matcher"] = matcher
    return {
        "test_case_id": data["test_case_id"],
        "category": data["category"],
        "severity": data["severity"],
        "input": data["input"],
        "expected_behavior": behavior,
        "metadata": data.get("metadata") or {},
    }


@router.post("/{suite_id}/import", response_model=TestSuiteResponse)
async def import_suite_version(
    suite_id: UUID,
    request: SuiteImportRequest,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Import a new version of an existing suite from inline YAML/JSON."""
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    if len(request.content.encode("utf-8")) > MAX_IMPORT_SIZE:
        raise ValidationError(f"Content too large (max {MAX_IMPORT_SIZE} bytes)")

    service = SuiteService(suite_repo, case_repo)
    if request.format.lower() == "json":
        data = json.loads(request.content)
    else:
        data = yaml.safe_load(request.content)

    if not isinstance(data, dict):
        raise ValidationError("Suite definition must be a mapping")

    data.setdefault("name", suite.name)
    data.setdefault("description", suite.description)

    updated = await service.create_version(
        suite_id, data, UUID(current_user.sub), changelog="Imported"
    )
    cases = await case_repo.list_by_suite(updated.id)
    return TestSuiteResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        version=updated.version,
        schema_version=updated.schema_version,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.delete("/{suite_id}")
async def delete_suite(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    deleted = await suite_repo.delete(suite_id)
    if not deleted:
        raise NotFoundError("TestSuite", str(suite_id))
    return {"message": "Suite deleted"}


class TestCaseCreate(BaseModel):
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior_type: str
    expected_behavior_matcher: dict = {}
    expected_behavior_rubric: dict | None = None
    metadata: dict = {}


class TestCaseUpdate(BaseModel):
    test_case_id: str | None = None
    category: TestCaseCategory | None = None
    severity: TestCaseSeverity | None = None
    input: str | None = None
    expected_behavior_type: str | None = None
    expected_behavior_matcher: dict | None = None
    expected_behavior_rubric: dict | None = None
    metadata: dict | None = None
    is_active: bool | None = None


@router.post("/{suite_id}/test-cases", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    suite_id: UUID,
    test_case: TestCaseCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    tc_data = _case_payload(test_case.model_dump())
    try:
        columns = _case_columns(tc_data)
    except (ValueError, PydanticValidationError) as e:
        raise ValidationError(f"Invalid test case: {e}") from e

    new_case = TestCase(
        suite_id=str(suite_id),
        test_case_id=test_case.test_case_id,
        created_by=UUID(current_user.sub),
        **columns,
    )
    new_case = await case_repo.create(new_case)

    version = TestCaseVersion(
        test_case_id=new_case.id,
        version=1,
        snapshot=tc_data,
        created_by=UUID(current_user.sub),
    )
    case_repo.session.add(version)
    await case_repo.session.flush()

    return _build_case_response(new_case)


@router.put("/{suite_id}/test-cases/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    suite_id: UUID,
    case_id: UUID,
    update: TestCaseUpdate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    case = await case_repo.get(case_id)
    # suite_id is stored as a string; compare as strings (UUID != str was always unequal).
    if not case or str(case.suite_id) != str(suite_id):
        raise NotFoundError("TestCase", str(case_id))

    update_data = update.model_dump(exclude_unset=True)
    current = {
        "test_case_id": case.test_case_id,
        "category": case.category.value,
        "severity": case.severity.value,
        "input": case.input,
        "expected_behavior_type": case.expected_behavior_type.value,
        "expected_behavior_matcher": case.matcher_config or {},
        "expected_behavior_rubric": case.rubric_config,
        "metadata": case.test_case_metadata or {},
    }
    if "expected_behavior_type" in update_data and "expected_behavior_matcher" not in update_data:
        current["expected_behavior_matcher"] = {}  # matcher fields belong to the old type
        current["expected_behavior_rubric"] = None
    merged = {**current, **{k: v for k, v in update_data.items() if v is not None and k != "is_active"}}
    tc_data = _case_payload(merged)
    try:
        columns = _case_columns(tc_data)
    except (ValueError, PydanticValidationError) as e:
        raise ValidationError(f"Invalid test case: {e}") from e

    for column, value in columns.items():
        setattr(case, column, value)
    if update.test_case_id:
        case.test_case_id = update.test_case_id
    if update.is_active is not None:
        case.is_active = update.is_active
    case.version += 1
    case.updated_at = datetime.utcnow()

    version = TestCaseVersion(
        test_case_id=case.id,
        version=case.version,
        snapshot=tc_data,
        created_by=UUID(current_user.sub),
    )
    case_repo.session.add(version)
    await case_repo.session.flush()

    return _build_case_response(case)


@router.delete("/{suite_id}/test-cases/{case_id}")
async def delete_test_case(
    suite_id: UUID,
    case_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    case = await case_repo.get(case_id)
    if not case or case.suite_id != suite_id:
        raise NotFoundError("TestCase", str(case_id))

    await case_repo.delete(case)
    return {"message": "Test case deleted"}
