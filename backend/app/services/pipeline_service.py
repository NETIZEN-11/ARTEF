"""End-to-end evaluation pipeline for one run.

execute -> score -> diff against the approved baseline -> classify severity -> gate -> route
to human review. Kept free of Celery so it can be called from the worker, the CLI and tests.

Fail-closed rules (PRD F2/F5/F7):
  * every executed test case gets a result; target or scoring errors are INCONCLUSIVE
  * inconclusive results fail the gate
  * no approved baseline -> gate FAIL until a human approves one
  * a pipeline crash marks the run FAILED (never left half-finished or passed)
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.enums import ReviewStatus, RunStatus, SeverityLevel, Verdict
from app.domain.value_objects import GateResult, RegressionFinding
from app.evaluation.cost.cost_tracker import CostTracker
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.models.review import ReviewQueue
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import (
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
    ReviewQueueRepository,
)
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import MockScoringService, ScoringService

settings = get_settings()
logger = get_logger(__name__)

REVIEW_SEVERITIES = {SeverityLevel.CRITICAL, SeverityLevel.HIGH}


def get_scoring_service_class() -> type[ScoringService]:
    if settings.EVAL_MODE == "local" or settings.DEV_MOCK_JUDGE:
        return MockScoringService
    return ScoringService


class EvaluationPipeline:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.run_repo = RunRepository(session)
        self.execution_repo = ExecutionRepository(session)
        self.result_repo = ResultRepository(session)
        self.agent_repo = TargetAgentRepository(session)
        self.case_repo = TestCaseRepository(session)
        self.baseline_repo = BaselineRepository(session)
        self.baseline_item_repo = BaselineItemRepository(session)
        self.regression_repo = RegressionRepository(session)
        self.review_repo = ReviewQueueRepository(session)

    async def run(self, run_id: UUID) -> GateResult | None:
        run = await self.run_repo.get(run_id)
        if not run:
            logger.error("run_not_found", run_id=str(run_id))
            return None
        if run.status == RunStatus.CANCELLED:
            return None

        execution_service = ExecutionService(
            self.run_repo, self.execution_repo, self.result_repo, self.agent_repo, self.case_repo
        )
        await execution_service.execute_run(run_id)
        await self.session.commit()  # make progress visible to the UI

        scoring_service = get_scoring_service_class()(
            self.execution_repo, self.result_repo, self.case_repo
        )
        await scoring_service.score_run(run_id)
        await self.session.commit()

        run = await self.run_repo.get(run_id)
        await self.session.refresh(run)
        if CostTracker().check_limits(run.total_cost_usd, 0)["run_limit_exceeded"]:
            raise RuntimeError(
                f"Run cost limit exceeded: ${run.total_cost_usd:.2f} > "
                f"${settings.COST_PER_RUN_LIMIT_USD:.2f}"
            )

        baseline = (
            await self.baseline_repo.get(run.baseline_id)
            if run.baseline_id
            else await self.baseline_repo.get_active_for_suite(run.suite_id)
        )
        findings: list[RegressionFinding] = []
        if baseline and settings.REGRESSION_DETECTION_ENABLED:
            run.baseline_id = baseline.id
            run.status = RunStatus.DIFFING
            await self.session.flush()
            detector = RegressionDetector(
                self.result_repo, self.baseline_repo, self.baseline_item_repo, self.regression_repo
            )
            findings = await detector.detect_regressions(
                run_id, baseline.id, classifier=SeverityClassifier(self.case_repo)
            )

        gate_result = await GateEvaluator(
            self.run_repo, self.result_repo, self.regression_repo
        ).evaluate(run_id, has_baseline=baseline is not None)

        await self._route_to_review(run_id, findings)
        await self.session.commit()
        logger.info("pipeline_completed", run_id=str(run_id), decision=gate_result.decision)
        return gate_result

    async def _route_to_review(self, run_id: UUID, findings: list[RegressionFinding]) -> None:
        """FR-009: Critical/High regressions and ambiguous (inconclusive) ones go to humans."""
        for finding in findings:
            ambiguous = finding.current_verdict == Verdict.INCONCLUSIVE
            if not finding.regression_id or not (finding.severity in REVIEW_SEVERITIES or ambiguous):
                continue
            result = await self.result_repo.get_by_run_and_test_case(run_id, finding.test_case_id)
            test_case = await self.case_repo.get(finding.test_case_id)
            await self.review_repo.create(
                ReviewQueue(
                    regression_id=finding.regression_id,
                    run_id=run_id,
                    severity=finding.severity,
                    confidence=result.confidence if result else 0.0,
                    category=test_case.category.value if test_case else "unknown",
                    status=ReviewStatus.PENDING,
                )
            )


async def mark_run_failed(session: AsyncSession, run_id: UUID, error: str) -> None:
    run = await RunRepository(session).get(run_id)
    if run is None:
        return
    run.status = RunStatus.FAILED
    run.error_message = error[:2000]
    run.completed_at = datetime.utcnow()
    await session.commit()
