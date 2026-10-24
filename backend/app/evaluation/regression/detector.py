from typing import Any
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.enums import RegressionType, SeverityLevel, Verdict
from app.domain.value_objects import EvidenceItem, RegressionFinding
from app.models.regression import Regression
from app.repositories.baselines import (
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
)
from app.repositories.runs import ResultRepository

logger = get_logger(__name__)


class RegressionDetector:
    def __init__(
        self,
        result_repo: ResultRepository,
        baseline_repo: BaselineRepository,
        baseline_item_repo: BaselineItemRepository,
        regression_repo: RegressionRepository,
    ):
        self.result_repo = result_repo
        self.baseline_repo = baseline_repo
        self.baseline_item_repo = baseline_item_repo
        self.regression_repo = regression_repo

    async def detect_regressions(
        self, run_id: UUID, baseline_id: UUID, classifier: Any = None
    ) -> list[RegressionFinding]:
        """Diff a run against a baseline and persist each regression.

        Only behaviour that got worse is a regression: PASS->FAIL, PASS->INCONCLUSIVE,
        INCONCLUSIVE->FAIL, and new tests that do not pass. Improvements are logged, not
        flagged. If a classifier is given, the final (deterministic) severity is applied
        before the row is saved, so the gate and the stored record agree.
        """
        baseline = await self.baseline_repo.get(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline", str(baseline_id))

        results = await self.result_repo.list_by_run(run_id)
        baseline_items = await self.baseline_item_repo.list_by_baseline(baseline_id)

        baseline_map = {str(item.test_case_id): item for item in baseline_items}
        findings = []

        for result in results:
            test_case_id = str(result.test_case_id)
            baseline_item = baseline_map.get(test_case_id)

            if not baseline_item:
                if result.verdict == Verdict.PASS:
                    continue  # a new test that passes is not a regression
                finding = RegressionFinding(
                    test_case_id=test_case_id,
                    previous_verdict=Verdict.INCONCLUSIVE,
                    current_verdict=result.verdict,
                    regression_type=RegressionType.NEW_FAILURE,
                    severity=SeverityLevel.MEDIUM,
                    evidence=[
                        EvidenceItem(source="detector", text="New test case not in baseline")
                    ],
                    baseline_run_id=str(baseline.run_id),
                    current_run_id=str(run_id),
                )
                findings.append(await self._save_regression(finding, run_id, baseline_id, classifier))
                continue

            previous = baseline_item.verdict
            current = result.verdict

            if previous == current:
                continue
            if current == Verdict.PASS:
                logger.info("test_improved", test_case_id=test_case_id, previous=previous.value)
                continue

            regression_type = self._classify_regression(previous, current)
            severity = self._determine_base_severity(previous, current, regression_type)

            finding = RegressionFinding(
                test_case_id=test_case_id,
                previous_verdict=previous,
                current_verdict=current,
                regression_type=regression_type,  # Use enum directly, not .value
                severity=severity,
                evidence=[
                    EvidenceItem(source="baseline", text=f"Baseline verdict: {previous.value}"),
                    EvidenceItem(source="current", text=f"Current verdict: {current.value}"),
                    EvidenceItem(
                        source="baseline", text=f"Baseline confidence: {baseline_item.confidence}"
                    ),
                    EvidenceItem(source="current", text=f"Current confidence: {result.confidence}"),
                ],
                baseline_run_id=str(baseline.run_id),
                current_run_id=str(run_id),
            )
            findings.append(await self._save_regression(finding, run_id, baseline_id, classifier))

        # Every executed test now produces a result (failed executions are INCONCLUSIVE), so a
        # baseline test with no result was removed or deactivated: suite drift, not a regression.
        result_ids = {str(r.test_case_id) for r in results}
        drifted = [tc_id for tc_id in baseline_map if tc_id not in result_ids]
        if drifted:
            logger.warning("suite_drift", run_id=str(run_id), missing_test_case_ids=drifted)

        return findings

    def _classify_regression(self, previous: Verdict, current: Verdict) -> RegressionType:
        if previous == Verdict.PASS and current == Verdict.FAIL:
            return RegressionType.PASS_TO_FAIL
        if previous == Verdict.PASS and current == Verdict.INCONCLUSIVE:
            return RegressionType.PASS_TO_INCONCLUSIVE
        if previous == Verdict.FAIL and current == Verdict.FAIL:
            return RegressionType.FAIL_TO_FAIL
        if previous == Verdict.FAIL and current == Verdict.PASS:
            return RegressionType.FAIL_TO_PASS
        if previous == Verdict.INCONCLUSIVE and current == Verdict.FAIL:
            return RegressionType.INCONCLUSIVE_TO_FAIL
        return RegressionType.NEW_FAILURE

    def _determine_base_severity(
        self, previous: Verdict, current: Verdict, regression_type: RegressionType
    ) -> SeverityLevel:
        if regression_type == RegressionType.PASS_TO_FAIL:
            return SeverityLevel.HIGH
        if (
            regression_type == RegressionType.PASS_TO_INCONCLUSIVE
            or regression_type == RegressionType.INCONCLUSIVE_TO_FAIL
        ):
            return SeverityLevel.MEDIUM
        if (
            regression_type == RegressionType.FAIL_TO_FAIL
            or regression_type == RegressionType.FAIL_TO_PASS
        ):
            return SeverityLevel.LOW
        return SeverityLevel.LOW

    async def _save_regression(
        self, finding: RegressionFinding, run_id: UUID, baseline_id: UUID, classifier: Any = None
    ) -> RegressionFinding:
        if classifier is not None:
            classification = await classifier.classify(finding)
            finding.severity = classification.level
            finding.evidence.append(EvidenceItem(source="severity", text=classification.rationale))
        regression = Regression(
            run_id=run_id,
            baseline_id=baseline_id,
            test_case_id=UUID(finding.test_case_id),
            previous_verdict=finding.previous_verdict,
            current_verdict=finding.current_verdict,
            regression_type=finding.regression_type,
            severity=finding.severity,
            evidence=[e.model_dump() for e in finding.evidence],
        )
        saved = await self.regression_repo.create(regression)
        finding.regression_id = str(saved.id) if getattr(saved, "id", None) else None
        return finding
