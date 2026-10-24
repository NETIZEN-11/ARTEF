from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import (
    TokenData,
    get_baseline_item_repo,
    get_baseline_repo,
    get_result_repo,
    get_run_repo,
    require_role,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.enums import RunStatus, Verdict
from app.repositories.runs import ResultRepository, RunRepository
from app.services.audit import record_audit
from app.models.baseline import Baseline, BaselineItem
from app.repositories.baselines import BaselineItemRepository, BaselineRepository

router = APIRouter()


class BaselineCreate(BaseModel):
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: str | None = None


class BaselineResponse(BaseModel):
    id: UUID
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: str | None = None
    framework_version: str = "1.0.0"
    model_versions: dict = {}
    prompt_versions: dict = {}
    approved_by: UUID | None = None
    approved_at: datetime | str | None = None
    is_active: bool = False
    created_at: datetime | str

    class Config:
        from_attributes = True


class BaselineItemResponse(BaseModel):
    id: UUID
    baseline_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    evidence: list[dict]

    class Config:
        from_attributes = True


@router.get("", response_model=list[BaselineResponse], include_in_schema=False)
@router.get("/", response_model=list[BaselineResponse])
async def list_baselines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    suite_id: UUID | None = None,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    filters = {}
    if suite_id:
        filters["suite_id"] = suite_id
    baselines = await baseline_repo.list(skip=skip, limit=limit, filters=filters)
    return [BaselineResponse.model_validate(b) for b in baselines]


@router.post("/", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    baseline: BaselineCreate,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    baseline_item_repo: BaselineItemRepository = Depends(get_baseline_item_repo),
    run_repo: RunRepository = Depends(get_run_repo),
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    """Approve a finished run as the suite's known-good baseline (replaces the active one)."""
    run = await run_repo.get(baseline.run_id)
    if not run:
        raise NotFoundError("Run", str(baseline.run_id))
    if str(run.suite_id) != str(baseline.suite_id):
        raise ValidationError("Run does not belong to this suite")
    if run.status not in (RunStatus.COMPLETED, RunStatus.REVIEW_REQUIRED):
        raise ValidationError(f"Only finished runs can be baselined (run is {run.status.value})")
    if run.inconclusive_count:
        raise ValidationError(
            f"Run has {run.inconclusive_count} inconclusive result(s); a baseline must have a "
            "definite PASS/FAIL verdict for every test"
        )
    if await baseline_repo.get_by_run(baseline.run_id):
        raise ConflictError("This run is already a baseline")

    await baseline_repo.deactivate_for_suite(baseline.suite_id)
    new_baseline = Baseline(
        **baseline.model_dump(),
        framework_version="1.0.0",
        model_versions={},
        prompt_versions={},
        approved_by=UUID(current_user.sub),
        approved_at=datetime.utcnow(),
    )
    new_baseline.is_active = True
    new_baseline = await baseline_repo.create(new_baseline)

    # Query results explicitly: run.results is a lazy relationship (unusable in async code).
    results = await result_repo.list_by_run(run.id)
    for result in results:
        await baseline_item_repo.create(
            BaselineItem(
                baseline_id=new_baseline.id,
                test_case_id=result.test_case_id,
                verdict=result.verdict,
                confidence=result.confidence,
                evidence=result.evidence,
            )
        )
    await record_audit(
        baseline_repo.session,
        current_user.sub,
        "baseline.approve",
        "baseline",
        new_baseline.id,
        {"run_id": str(run.id), "suite_id": str(run.suite_id), "items": len(results)},
    )

    return BaselineResponse.model_validate(new_baseline)


@router.get("/suite/{suite_id}/active", response_model=Optional[BaselineResponse])
async def get_active_baseline(
    suite_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    baseline = await baseline_repo.get_active_for_suite(suite_id)
    if not baseline:
        return None
    return BaselineResponse.model_validate(baseline)


@router.get("/{baseline_id}", response_model=BaselineResponse)
async def get_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))
    return BaselineResponse.model_validate(baseline)


@router.get("/{baseline_id}/items", response_model=list[BaselineItemResponse])
async def list_baseline_items(
    baseline_id: UUID,
    baseline_item_repo: BaselineItemRepository = Depends(get_baseline_item_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    items = await baseline_item_repo.list_by_baseline(baseline_id)
    return [BaselineItemResponse.model_validate(item) for item in items]


@router.post("/{baseline_id}/approve")
async def approve_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))

    if baseline.is_active:
        raise ConflictError("Baseline already approved")

    await baseline_repo.deactivate_for_suite(baseline.suite_id, keep_id=baseline.id)
    baseline.is_active = True
    baseline.approved_by = UUID(current_user.sub)
    baseline.approved_at = datetime.utcnow()
    await baseline_repo.session.flush()
    await record_audit(
        baseline_repo.session, current_user.sub, "baseline.approve", "baseline", baseline.id
    )

    return {"message": "Baseline approved"}


@router.delete("/{baseline_id}")
async def delete_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Baselines are never hard-deleted: their regressions and review items (the evidence
    trail) cascade from them. Deactivate instead."""
    if not await baseline_repo.get(baseline_id):
        raise NotFoundError("Baseline", str(baseline_id))
    raise ConflictError(
        "Baselines are kept for the audit trail and cannot be deleted. Deactivate it instead."
    )


@router.post("/{baseline_id}/deactivate")
async def deactivate_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))

    baseline.is_active = False
    await baseline_repo.session.flush()
    await record_audit(
        baseline_repo.session, current_user.sub, "baseline.deactivate", "baseline", baseline.id
    )

    return {"message": "Baseline deactivated"}
