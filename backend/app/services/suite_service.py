from datetime import datetime
from uuid import UUID

import jsonschema
import yaml

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.enums import ExpectedBehaviorType, TestCaseCategory, TestCaseSeverity
from app.domain.value_objects import (
    ExpectedBehavior,
    LLMRubric,
    MatcherConfig,
    TestCaseMetadata,
)
from app.models.test_suite import TestCase, TestCaseVersion, TestSuite, TestSuiteVersion
from app.repositories.suites import TestCaseRepository, TestSuiteRepository

SUITE_SCHEMA = {
    "type": "object",
    "required": ["name", "test_cases"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 255},
        "description": {"type": "string"},
        "schema_version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["test_case_id", "category", "severity", "input", "expected_behavior"],
                "properties": {
                    "test_case_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100,
                        "pattern": "^[a-zA-Z0-9_-]+$",
                    },
                    "category": {"type": "string", "enum": [c.value for c in TestCaseCategory]},
                    "severity": {"type": "string", "enum": [s.value for s in TestCaseSeverity]},
                    "input": {"type": "string", "minLength": 1},
                    "expected_behavior": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [e.value for e in ExpectedBehaviorType],
                            },
                            "matcher": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": [e.value for e in ExpectedBehaviorType],
                                    },
                                    "pattern": {"type": "string"},
                                    "keywords": {"type": "array", "items": {"type": "string"}},
                                    "case_sensitive": {"type": "boolean"},
                                    "regex_timeout_ms": {
                                        "type": "integer",
                                        "minimum": 100,
                                        "maximum": 10000,
                                    },
                                    "expected_keys": {"type": "array", "items": {"type": "string"}},
                                    "required_fields": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "rubric": {
                                "type": "object",
                                "properties": {
                                    "criteria": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["name", "description"],
                                            "properties": {
                                                "name": {"type": "string"},
                                                "description": {"type": "string"},
                                                "weight": {
                                                    "type": "number",
                                                    "minimum": 0,
                                                    "maximum": 1,
                                                },
                                                "pass_threshold": {
                                                    "type": "number",
                                                    "minimum": 0,
                                                    "maximum": 1,
                                                },
                                            },
                                        },
                                    },
                                    "overall_threshold": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                    "require_evidence": {"type": "boolean"},
                                },
                            },
                        },
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "author": {"type": "string"},
                            "description": {"type": "string"},
                            "references": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "minItems": 1,
        },
    },
}


def _case_columns(tc_data: dict) -> dict:
    """Map a validated suite test case onto TestCase columns.

    The value objects re-validate the matcher (e.g. regex compiles) and rubric; they are
    then stored as plain JSON, the same shape the seed script and the scorer use.
    """
    expected_behavior = tc_data["expected_behavior"]
    matcher = expected_behavior.get("matcher")
    rubric = expected_behavior.get("rubric")
    expected = ExpectedBehavior(
        type=ExpectedBehaviorType(expected_behavior["type"]),
        matcher=MatcherConfig(**matcher) if matcher else None,
        rubric=LLMRubric(**rubric) if rubric else None,
    )
    return {
        "category": TestCaseCategory(tc_data["category"]),
        "severity": TestCaseSeverity(tc_data["severity"]),
        "input": tc_data["input"],
        "expected_behavior_type": expected.type,
        "matcher_config": expected.matcher.model_dump(mode="json", exclude_none=True) if expected.matcher else None,
        "rubric_config": expected.rubric.model_dump(mode="json", exclude_none=True) if expected.rubric else None,
        "test_case_metadata": TestCaseMetadata(**tc_data.get("metadata", {})).model_dump(mode="json", exclude_none=True),
    }


class SuiteService:
    def __init__(self, suite_repo: TestSuiteRepository, case_repo: TestCaseRepository):
        self.suite_repo = suite_repo
        self.case_repo = case_repo

    async def validate_suite(self, data: dict) -> dict:
        try:
            jsonschema.validate(instance=data, schema=SUITE_SCHEMA)
        except jsonschema.ValidationError as e:
            raise ValidationError(f"Suite validation failed: {e.message}", {"path": list(e.path)})

        test_case_ids = [tc["test_case_id"] for tc in data["test_cases"]]
        if len(test_case_ids) != len(set(test_case_ids)):
            raise ValidationError("Duplicate test_case_id values found")

        return data

    async def create_suite(self, data: dict, user_id: UUID) -> TestSuite:
        validated = await self.validate_suite(data)

        existing = await self.suite_repo.get_by_name(validated["name"])
        if existing:
            raise ConflictError(f"Suite with name '{validated['name']}' already exists")

        suite = TestSuite(
            name=validated["name"],
            description=validated.get("description"),
            schema_version=validated.get("schema_version", "1.0"),
            created_by=user_id,
        )
        suite = await self.suite_repo.create(suite)

        test_cases = []
        for tc_data in validated["test_cases"]:
            test_case = await self._create_test_case(suite.id, tc_data, user_id)
            test_cases.append(test_case)

        version = TestSuiteVersion(
            suite_id=suite.id,
            version=suite.version,
            snapshot=validated,
            created_by=user_id,
        )
        self.suite_repo.session.add(version)

        await self.suite_repo.session.flush()
        return suite

    async def _create_test_case(self, suite_id: UUID, tc_data: dict, user_id: UUID) -> TestCase:
        test_case = TestCase(
            suite_id=suite_id,
            test_case_id=tc_data["test_case_id"],
            created_by=user_id,
            **_case_columns(tc_data),
        )
        test_case = await self.case_repo.create(test_case)

        version = TestCaseVersion(
            test_case_id=test_case.id,
            version=1,
            snapshot=tc_data,
            created_by=user_id,
        )
        self.case_repo.session.add(version)

        return test_case

    async def import_yaml(self, yaml_content: str, user_id: UUID) -> TestSuite:
        MAX_YAML_SIZE = 5 * 1024 * 1024  # 5MB
        if len(yaml_content) > MAX_YAML_SIZE:
            raise ValidationError(f"YAML file too large (max {MAX_YAML_SIZE / 1024 / 1024}MB)")

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        return await self.create_suite(data, user_id)

    async def import_json(self, json_content: str, user_id: UUID) -> TestSuite:
        import json

        MAX_JSON_SIZE = 5 * 1024 * 1024  # 5MB
        if len(json_content) > MAX_JSON_SIZE:
            raise ValidationError(f"JSON file too large (max {MAX_JSON_SIZE / 1024 / 1024}MB)")

        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        return await self.create_suite(data, user_id)

    async def get_suite_with_cases(self, suite_id: UUID) -> tuple[TestSuite, list[TestCase]] | None:
        # Return cases alongside the suite rather than assigning suite.test_cases: replacing
        # a relationship collection forces a lazy load, which async sessions cannot do.
        suite = await self.suite_repo.get(suite_id)
        if not suite:
            return None
        return suite, await self.case_repo.list_by_suite(suite_id)

    async def create_version(
        self, suite_id: UUID, data: dict, user_id: UUID, changelog: str = ""
    ) -> TestSuite:
        suite = await self.suite_repo.get(suite_id)
        if not suite:
            raise NotFoundError("TestSuite", str(suite_id))

        validated = await self.validate_suite(data)

        suite.version += 1
        suite.updated_at = datetime.utcnow()

        for tc_data in validated["test_cases"]:
            existing = await self.case_repo.get_by_suite_and_id(suite_id, tc_data["test_case_id"])
            if existing:
                existing.version += 1
                for column, value in _case_columns(tc_data).items():
                    setattr(existing, column, value)
                existing.updated_at = datetime.utcnow()

                version = TestCaseVersion(
                    test_case_id=existing.id,
                    version=existing.version,
                    snapshot=tc_data,
                    created_by=user_id,
                )
                self.case_repo.session.add(version)
            else:
                await self._create_test_case(suite_id, tc_data, user_id)

        version = TestSuiteVersion(
            suite_id=suite.id,
            version=suite.version,
            snapshot=validated,
            changelog=changelog,
            created_by=user_id,
        )
        self.suite_repo.session.add(version)

        await self.suite_repo.session.flush()
        return suite
