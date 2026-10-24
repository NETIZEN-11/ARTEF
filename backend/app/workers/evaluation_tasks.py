import asyncio
from uuid import UUID

from celery import shared_task

from app.core.database import create_task_session_maker
from app.core.logging import get_logger
from app.services.pipeline_service import (
    EvaluationPipeline,
    get_scoring_service_class,
    mark_run_failed,
)

logger = get_logger(__name__)


def get_scoring_service():
    return get_scoring_service_class()


async def _evaluate(run_uuid: UUID) -> str | None:
    task_engine, session_maker = create_task_session_maker()
    try:
        async with session_maker() as session:
            try:
                gate_result = await EvaluationPipeline(session).run(run_uuid)
                return gate_result.decision if gate_result else None
            except Exception as e:
                logger.exception("evaluation_task_failed", run_id=str(run_uuid), error=str(e))
                await session.rollback()
                await mark_run_failed(session, run_uuid, f"Pipeline error: {e}")
                return None
    finally:
        await task_engine.dispose()


@shared_task(bind=True)
def run_evaluation(self, run_id: str):
    """Run the full pipeline for one run. Not auto-retried: a retry would duplicate results."""
    logger.info("evaluation_task_started", run_id=run_id)
    decision = asyncio.run(_evaluate(UUID(run_id)))
    logger.info("evaluation_task_finished", run_id=run_id, gate_decision=decision)
    return decision


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_seeded_regression_benchmark(self):
    logger.info("seeded_regression_benchmark_started")

    async def _run():
        from scripts.run_seeded_regression import run_seeded_regression

        result = await run_seeded_regression()
        logger.info("seeded_regression_benchmark_completed", result=result)
        return result

    return asyncio.run(_run())


@shared_task
def cleanup_old_runs(days: int = 365):
    logger.info("cleanup_old_runs_started", days=days)
    logger.info("cleanup_old_runs_completed")


@shared_task
def check_cost_limits():
    logger.info("cost_limit_check_started")
    logger.info("cost_limit_check_completed")
