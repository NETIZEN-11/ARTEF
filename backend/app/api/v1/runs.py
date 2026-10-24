import asyncio
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.api.deps import (
    TokenData,
    get_agent_repo,
    get_baseline_repo,
    get_execution_repo,
    get_result_repo,
    get_review_repo,
    get_run_repo,
    get_suite_repo,
    require_role,
)
from app.core.database import get_async_session
from app.core.exceptions import ConflictError, NotFoundError, TaskQueueUnavailableError
from app.core.logging import get_logger
from app.domain.enums import RunStatus
from app.models.run import Run
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import BaselineRepository, ReviewQueueRepository
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestSuiteRepository
from app.workers.celery_app import celery_app
from app.workers.evaluation_tasks import run_evaluation

router = APIRouter()
logger = get_logger(__name__)


class RunCreate(BaseModel):
    target_agent_id: UUID
    suite_id: UUID
    suite_version: int | None = None
    baseline_id: UUID | None = None


class RunResponse(BaseModel):
    id: UUID
    target_agent_id: UUID
    target_agent_name: str | None = None
    suite_id: UUID
    suite_name: str | None = None
    suite_version: int | None = 1
    baseline_id: UUID | None = None
    status: RunStatus
    framework_version: str = "1.0.0"
    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0
    regression_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    started_at: datetime | str | None = None
    completed_at: datetime | str | None = None
    created_at: datetime | str
    error_message: str | None = None
    gate_decision: str | None = None
    gate_summary: str | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[RunResponse], include_in_schema=False)
@router.get("/", response_model=list[RunResponse])
async def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    target_agent_id: UUID | None = None,
    suite_id: UUID | None = None,
    status: RunStatus | None = None,
    sort: str | None = Query(
        default=None,
        description="Sort field in 'field:direction' format, currently supported: created_at:desc",
    ),
    run_repo: RunRepository = Depends(get_run_repo),
    response: Response = None,
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    filters = {}
    if target_agent_id:
        filters["target_agent_id"] = target_agent_id
    if suite_id:
        filters["suite_id"] = suite_id
    if status:
        filters["status"] = status

    order_by = None
    descending = False
    if sort:
        parts = sort.split(":", 1)
        field = parts[0].strip()
        direction = parts[1].strip().lower() if len(parts) > 1 else "asc"
        if field not in {"created_at"}:
            raise HTTPException(status_code=400, detail=f"Unsupported sort field: {field}")
        if direction not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail=f"Unsupported sort direction: {direction}")
        order_by = field
        descending = direction == "desc"

    runs = await run_repo.list_scalars(
        skip=skip, limit=limit, filters=filters, order_by=order_by, descending=descending
    )
    total = await run_repo.count(filters=filters)
    # The body stays a bare array (existing clients depend on it); the total is
    # exposed through a header so the UI can paginate without a second
    # round-trip.
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(limit)
    response.headers["X-Page-Offset"] = str(skip)
    return [RunResponse.model_validate(run) for run in runs]


class StatsResponse(BaseModel):
    total_runs: int
    pass_rate: float
    total_regressions: int
    critical_findings: int
    review_queue_count: int
    avg_runtime: float
    total_cost: float
    high_count: int
    medium_count: int
    low_count: int
    pass_rate_trend: list[float] = []
    regression_trend: list[int] = []
    cost_trend: list[float] = []


async def _aggregate_in_own_session(run_repo: RunRepository) -> dict:
    """Run the aggregate on a dedicated session.

    An ``AsyncSession`` must not be used by two concurrent coroutines, so the
    aggregate is executed in its own session rather than sharing the
    request's session.
    """
    async with get_async_session() as session:
        return await RunRepository(session).aggregate_stats()


async def _count_pending_in_own_session(review_repo: ReviewQueueRepository) -> int:
    async with get_async_session() as session:
        return await ReviewQueueRepository(session).count_pending()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    run_repo: RunRepository = Depends(get_run_repo),
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    # Aggregates are computed in SQL: a single GROUP BY over `runs` instead of
    # loading hundreds of fully-hydrated Run rows and summing in Python.
    #
    # The two aggregates run on *separate* sessions: an AsyncSession is not
    # safe for concurrent use, so `asyncio.gather` on a single session raises
    # `IllegalStateChangeError` during teardown.
    totals, review_queue_count = await asyncio.gather(
        _aggregate_in_own_session(run_repo),
        _count_pending_in_own_session(review_repo),
    )

    total_runs = totals["total_runs"]
    total_tests = totals["total_tests"]
    total_passed = totals["passed"]
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

    total_regressions = totals["regressions"]
    critical_findings = totals["critical"]
    high_count = totals["high"]
    medium_count = totals["medium"]
    low_count = totals["low"]

    total_latency = totals["total_latency"]
    avg_runtime = total_latency / total_runs if total_runs > 0 else 0.0

    total_cost = totals["total_cost"]

    completed_runs = await run_repo.list_completed_trend(limit=7)

    pass_rate_trend = []
    regression_trend = []
    cost_trend = []

    for run in completed_runs:
        if run.total_tests > 0:
            pass_rate_trend.append((run.passed_count / run.total_tests) * 100)
        else:
            pass_rate_trend.append(0.0)
        regression_trend.append(run.regression_count if run.regression_count else 0)
        cost_trend.append(run.total_cost_usd if run.total_cost_usd else 0.0)

    return StatsResponse(
        total_runs=total_runs,
        pass_rate=pass_rate,
        total_regressions=total_regressions,
        critical_findings=critical_findings,
        review_queue_count=review_queue_count,
        avg_runtime=avg_runtime,
        total_cost=total_cost,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        pass_rate_trend=pass_rate_trend,
        regression_trend=regression_trend,
        cost_trend=cost_trend
    )


def _run_in_process(run_id: str) -> None:
    logger.info("run_eager_dispatch", run_id=run_id)
    run_evaluation.apply(args=[run_id])


@router.post("", response_model=RunResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=RunResponse, status_code=201)
async def create_run(
    run: RunCreate,
    background_tasks: BackgroundTasks,
    run_repo: RunRepository = Depends(get_run_repo),
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer"])
    ),
):
    agent = await agent_repo.get(run.target_agent_id)
    if not agent:
        raise NotFoundError("TargetAgent", str(run.target_agent_id))

    suite = await suite_repo.get(run.suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(run.suite_id))

    baseline = None
    if run.baseline_id:
        baseline = await baseline_repo.get(run.baseline_id)
        if not baseline:
            raise NotFoundError("Baseline", str(run.baseline_id))
    else:
        baseline = await baseline_repo.get_active_for_suite(suite.id)

    new_run = Run(
        target_agent_id=run.target_agent_id,
        suite_id=run.suite_id,
        suite_version=suite.version,
        baseline_id=baseline.id if baseline else None,
        framework_version="1.0.0",
        model_versions={},
        prompt_versions={},
        config_snapshot={},
        created_by=UUID(current_user.sub),
    )
    new_run = await run_repo.create(new_run)
    # Commit before dispatching so the worker can see the run.
    await run_repo.session.commit()

    if celery_app.conf.task_always_eager:
        # Dev/test mode: run in-process after the response is sent.
        background_tasks.add_task(_run_in_process, str(new_run.id))
    else:
        try:
            run_evaluation.apply_async(args=[str(new_run.id)], retry=False)
        except Exception as e:
            logger.error("run_dispatch_failed", run_id=str(new_run.id), error=str(e))
            new_run.status = RunStatus.FAILED
            new_run.error_message = f"Could not queue run: {e}"
            new_run.completed_at = datetime.utcnow()
            await run_repo.session.commit()
            raise TaskQueueUnavailableError({"run_id": str(new_run.id)}) from e

    logger.info(
        "run_created", run_id=str(new_run.id), suite_id=str(suite.id), agent_id=str(agent.id)
    )
    return RunResponse.model_validate(new_run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    run = await run_repo.get(run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))
    return RunResponse.model_validate(run)


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    run = await run_repo.get(run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))

    if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        raise ConflictError(f"Cannot cancel run in status {run.status}")

    run.status = RunStatus.CANCELLED
    run.completed_at = datetime.utcnow()
    await run_repo.session.flush()

    return {"message": "Run cancelled"}


@router.get("/{run_id}/executions")
async def list_executions(
    run_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    executions = await execution_repo.list_by_run(run_id, skip=skip, limit=limit)
    return [
        {
            "id": str(e.id),
            "test_case_id": str(e.test_case_id),
            "status": e.status.value,
            "latency_ms": e.latency_ms,
        }
        for e in executions
    ]


@router.get("/{run_id}/results")
async def list_results(
    run_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    results = await result_repo.list_by_run(run_id, skip=skip, limit=limit)
    return [
        {
            "id": str(r.id),
            "test_case_id": str(r.test_case_id),
            "verdict": r.verdict.value,
            "confidence": r.confidence,
            "execution_time_ms": r.execution_time_ms,
        }
        for r in results
    ]
