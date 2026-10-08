from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    BUILDING_MATRIX = "building_matrix"
    SCHEDULING = "scheduling"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    COMPARING_BASELINE = "comparing_baseline"
    CLASSIFYING_SEVERITY = "classifying_severity"
    EVALUATING_GATE = "evaluating_gate"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStep(BaseModel):
    name: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Configuration for an evaluation pipeline."""
    name: str
    description: str | None = None

    dataset_id: UUID
    dataset_version: int | None = None

    suite_id: UUID
    suite_version: int | None = None

    target_agent_id: UUID

    models: list[dict[str, Any]] = Field(default_factory=list)  # model_id, provider, parameters
    prompt_versions: list[UUID] = Field(default_factory=list)
    provider_configs: list[dict[str, Any]] = Field(default_factory=list)

    judge_config: dict[str, Any] | None = None
    redteam_config: dict[str, Any] | None = None
    regression_detection_enabled: bool = True
    cost_limit_usd: float | None = None

    baseline_id: UUID | None = None
    auto_baseline: bool = False  # Create baseline from first run

    max_parallel_cells: int = 4
    timeout_seconds: int = 3600
    retry_failed_cells: bool = True
    max_retries: int = 2

    gate_config: dict[str, Any] | None = None
    require_human_review: bool = True

    tags: list[str] = Field(default_factory=list)
    created_by: UUID | None = None


class PipelineResult(BaseModel):
    pipeline_id: UUID
    status: PipelineStatus
    config: PipelineConfig

    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_seconds: float | None = None

    total_cells: int = 0
    completed_cells: int = 0
    failed_cells: int = 0

    passed_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0

    regression_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    total_cost_usd: float = 0.0

    gate_decision: str | None = None
    gate_exit_code: int | None = None

    release_decision: str | None = None  # READY, WARNING, NEEDS_REVIEW, BLOCKED

    review_required: bool = False
    review_ids: list[UUID] = Field(default_factory=list)

    steps: list[PipelineStep] = Field(default_factory=list)

    error: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """Persistent pipeline run record."""
    id: UUID = Field(default_factory=uuid4)
    config: PipelineConfig
    status: PipelineStatus = PipelineStatus.QUEUED
    result: PipelineResult | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID | None = None
