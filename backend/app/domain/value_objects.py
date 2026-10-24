from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import (
    ExpectedBehaviorType,
    SeverityLevel,
    Verdict,
)


class MatcherConfig(BaseModel):
    type: ExpectedBehaviorType | None = None
    pattern: str | None = None
    keywords: list[str] | None = None
    case_sensitive: bool = False
    regex_timeout_ms: int = 1000
    expected_keys: list[str] | None = None
    required_fields: list[str] | None = None

    @field_validator("pattern")
    @classmethod
    def validate_regex(cls, v: str | None) -> str | None:
        if v is not None:
            import re

            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v


class LLMRubricCriterion(BaseModel):
    name: str
    description: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class LLMRubric(BaseModel):
    criteria: list[LLMRubricCriterion]
    overall_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    require_evidence: bool = True


class TestCaseMetadata(BaseModel):
    tags: list[str] = Field(default_factory=list)
    author: str | None = None
    description: str | None = None
    references: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class ExpectedBehavior(BaseModel):
    type: ExpectedBehaviorType
    matcher: MatcherConfig | None = None
    rubric: LLMRubric | None = None
    custom_validator: str | None = None


class EvidenceItem(BaseModel):
    """Structured evidence item for reproducibility and traceability."""
    source: str
    text: str
    trace_id: str | None = None
    span_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collected_by: str | None = None  # component that collected this evidence
    content_hash: str | None = None  # SHA256 of the text for integrity verification


class CriteriaResult(BaseModel):
    criterion: str
    passed: bool
    evidence: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class JudgeOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    criteria_results: list[CriteriaResult] = Field(default_factory=list)
    # Provider provenance (tokens, cost, model, provider id). Declared
    # explicitly so it survives validation instead of being silently dropped
    # by Pydantic's default "ignore extra" behaviour.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence_not_empty(self) -> "JudgeOutput":
        # A field_validator on ``evidence`` never runs when the field is
        # omitted (Pydantic skips validators for unset defaulted fields), so
        # the rule is enforced here where ``verdict`` is always available.
        if self.verdict in (Verdict.PASS, Verdict.FAIL) and not self.evidence:
            raise ValueError(f"Evidence list cannot be empty for {self.verdict} verdict")
        return self

    @field_validator("criteria_results")
    @classmethod
    def validate_criteria_consistency(cls, v: list[CriteriaResult]) -> list[CriteriaResult]:
        for criterion in v:
            if criterion.passed and criterion.confidence < 0.5:
                raise ValueError(f"Criterion '{criterion.criterion}' passed but confidence too low")
        return v


class ScoringResult(BaseModel):
    test_case_id: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    matcher_used: ExpectedBehaviorType | None = None
    judge_output: JudgeOutput | None = None
    second_judge_output: JudgeOutput | None = None
    judge_agreement: bool = True
    evidence: list[EvidenceItem] = Field(default_factory=list)
    execution_time_ms: int
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: list[str] = Field(default_factory=list)


class RegressionFinding(BaseModel):
    test_case_id: str
    previous_verdict: Verdict
    current_verdict: Verdict
    regression_type: str
    severity: SeverityLevel
    evidence: list[EvidenceItem] = Field(default_factory=list)
    baseline_run_id: str
    current_run_id: str
    regression_id: str | None = None  # id of the persisted Regression row, once saved


class SeverityClassification(BaseModel):
    level: SeverityLevel
    rationale: str
    deterministic_override: bool = False
    categories: list[str] = Field(default_factory=list)


class GateResult(BaseModel):
    decision: str
    exit_code: int
    regressions: list[RegressionFinding] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    inconclusive_count: int = 0
    infrastructure_failure: bool = False
    summary: str = ""


class CostBreakdown(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_provider: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EvidencePackage(BaseModel):
    """Complete evidence package for a single evaluation cell - immutable and reproducible."""
    evaluation_id: str
    test_case_id: str
    cell_id: str | None = None
    trace_id: str
    span_id: str

    test_input: str
    expected_behavior: str
    actual_response: str

    assertion_evidence: list[EvidenceItem] = Field(default_factory=list)
    judge_evidence: list[EvidenceItem] = Field(default_factory=list)
    redteam_evidence: list[EvidenceItem] = Field(default_factory=list)

    assertion_result: dict[str, Any] | None = None
    judge_result: dict[str, Any] | None = None
    redteam_result: dict[str, Any] | None = None

    final_verdict: str
    final_confidence: float
    final_severity: str | None = None

    execution_time_ms: int
    tokens_used: int
    estimated_cost: float
    model_info: dict[str, str] = Field(default_factory=dict)
    provider_info: dict[str, str] = Field(default_factory=dict)
    prompt_version: str | None = None
    dataset_version: str | None = None

    started_at: datetime
    completed_at: datetime

    package_hash: str | None = None  # SHA256 of the entire package for integrity

    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    reproducibility_verified: bool = False
    reproducibility_check_at: datetime | None = None
    reproducibility_check_result: dict[str, Any] | None = None
