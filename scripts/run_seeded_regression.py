#!/usr/bin/env python3
"""Run seeded regression benchmark to validate the framework."""

import app.core.sqlite_compat  # noqa: F401
import asyncio
import sys
import uuid
from datetime import datetime
from typing import Any, Dict

from app.core.database import async_session_maker, engine
from app.domain.enums import (
    ExecutionStatus,
    RunStatus,
    SeverityLevel,
    TestCaseCategory,
    Verdict,
)
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.models.baseline import Baseline, BaselineItem
from app.models.run import Execution, Run
from app.providers.target_agent import MockTargetAgentProvider
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import (
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
)
from app.repositories.runs import (
    ExecutionRepository,
    ResultRepository,
    RunRepository,
)
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import MockScoringService


async def run_seeded_regression() -> Dict[str, Any]:
    """Run the complete seeded regression benchmark."""
    async with async_session_maker() as session:
        # Get repositories
        agent_repo = TargetAgentRepository(session)
        suite_repo = TestSuiteRepository(session)
        case_repo = TestCaseRepository(session)
        run_repo = RunRepository(session)
        execution_repo = ExecutionRepository(session)
        result_repo = ResultRepository(session)
        baseline_repo = BaselineRepository(session)
        baseline_item_repo = BaselineItemRepository(session)
        regression_repo = RegressionRepository(session)

        # Get or create test agents
        safe_agent = (
            await agent_repo.get_by_name("Mock Target Agent v1 (Safe)")
            or await agent_repo.get_by_name("Safe Agent (Mock)")
        )
        vulnerable_agent = (
            await agent_repo.get_by_name("Mock Target Agent v2 (Vulnerable)")
            or await agent_repo.get_by_name("Vulnerable Agent (Mock)")
        )

        if not safe_agent or not vulnerable_agent:
            print("[FAIL] Required mock agents not found.")
            return {"success": False, "error": "Mock agents not found"}

        # Get test suites
        suites = await suite_repo.list(filters={"is_active": True})
        if not suites:
            print("[FAIL] No test suites found.")
            return {"success": False, "error": "Test suites not found"}

        # Target suite: prioritize jailbreak tests suite
        target_suite = None
        for s in suites:
            if "jailbreak" in s.name.lower():
                target_suite = s
                break
        if not target_suite:
            for s in suites:
                cases = await case_repo.list_by_suite(s.id)
                if any(c.category == TestCaseCategory.JAILBREAK for c in cases):
                    target_suite = s
                    break
        if not target_suite:
            target_suite = suites[0]

        print(f"[INFO] Selected Test Suite: '{target_suite.name}' (v{target_suite.version})")
        print("[PHASE 1] Establishing baseline with safe agent...")

        # Create baseline run with safe agent
        baseline_run = Run(
            target_agent_id=safe_agent.id,
            suite_id=target_suite.id,
            suite_version=target_suite.version,
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            config_snapshot={},
            status=RunStatus.QUEUED,
        )
        baseline_run = await run_repo.create(baseline_run)

        # Execute baseline run
        safe_provider = MockTargetAgentProvider(scenario="safe")

        async def mock_execute_run(run_id: uuid.UUID):
            run = await run_repo.get(run_id)
            if not run:
                return

            test_cases = await case_repo.list_by_suite(run.suite_id)
            run.total_tests = len(test_cases)
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow()
            await session.flush()

            for test_case in test_cases:
                execution = Execution(
                    run_id=run.id,
                    test_case_id=test_case.id,
                    status=ExecutionStatus.COMPLETED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    target_request={"input": test_case.input},
                    target_response=await safe_provider.call(test_case.input),
                    latency_ms=100,
                )
                await execution_repo.create(execution)

            run.status = RunStatus.SCORING
            await session.flush()
            return run

        await mock_execute_run(baseline_run.id)

        # Score baseline run
        scoring_service = MockScoringService(execution_repo, result_repo, case_repo)
        await scoring_service.score_run(baseline_run.id)

        # Create baseline
        baseline = Baseline(
            suite_id=target_suite.id,
            suite_version=target_suite.version,
            run_id=baseline_run.id,
            name=f"Baseline-{uuid.uuid4().hex[:6]}",
            description="Baseline established with safe agent",
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            approved_by=uuid.uuid4(),
            approved_at=datetime.utcnow(),
            is_active=True,
        )
        baseline = await baseline_repo.create(baseline)

        # Create baseline items
        baseline_results = await result_repo.list_by_run(baseline_run.id)
        for result in baseline_results:
            item = BaselineItem(
                baseline_id=baseline.id,
                test_case_id=result.test_case_id,
                verdict=result.verdict,
                confidence=result.confidence,
                evidence=result.evidence,
            )
            await baseline_item_repo.create(item)

        print(f"[OK] Baseline established: {baseline.id}")

        print("[PHASE 2] Running evaluation with vulnerable agent...")

        # Create test run with vulnerable agent
        test_run = Run(
            target_agent_id=vulnerable_agent.id,
            suite_id=target_suite.id,
            suite_version=target_suite.version,
            baseline_id=baseline.id,
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            config_snapshot={},
            status=RunStatus.QUEUED,
        )
        test_run = await run_repo.create(test_run)

        # Execute test run with vulnerable provider
        vulnerable_provider = MockTargetAgentProvider(scenario="jailbreak_vulnerable")

        async def mock_execute_vulnerable(run_id: uuid.UUID):
            run = await run_repo.get(run_id)
            if not run:
                return

            test_cases = await case_repo.list_by_suite(run.suite_id)
            run.total_tests = len(test_cases)
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow()
            await session.flush()

            for test_case in test_cases:
                execution = Execution(
                    run_id=run.id,
                    test_case_id=test_case.id,
                    status=ExecutionStatus.COMPLETED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    target_request={"input": test_case.input},
                    target_response=await vulnerable_provider.call(test_case.input),
                    latency_ms=100,
                )
                await execution_repo.create(execution)

            run.status = RunStatus.SCORING
            await session.flush()
            return run

        await mock_execute_vulnerable(test_run.id)

        # Score test run
        await scoring_service.score_run(test_run.id)

        print("[PHASE 3] Detecting regressions...")

        # Detect regressions
        detector = RegressionDetector(
            result_repo, baseline_repo, baseline_item_repo, regression_repo
        )
        findings = await detector.detect_regressions(test_run.id, baseline.id)

        print(f"[INFO] Found {len(findings)} potential regressions")

        # Classify severity
        classifier = SeverityClassifier(case_repo)
        for finding in findings:
            classification = await classifier.classify(finding)
            finding.severity = classification.level

        # Update database regression records with classified severity
        db_regressions = await regression_repo.list_by_run(test_run.id)
        for reg in db_regressions:
            for finding in findings:
                if str(reg.test_case_id) == str(finding.test_case_id):
                    reg.severity = finding.severity
        await session.flush()

        print("[PHASE 4] Evaluating CI gate...")

        # Evaluate gate
        gate_evaluator = GateEvaluator(run_repo, result_repo, regression_repo)
        gate_result = await gate_evaluator.evaluate(test_run.id)

        print(f"[GATE] Decision: {gate_result.decision} (Exit Code: {gate_result.exit_code})")
        print(f"   Critical: {gate_result.critical_count}, High: {gate_result.high_count}")
        print(f"   Medium: {gate_result.medium_count}, Low: {gate_result.low_count}")

        # Verify all seeded regressions detected
        seeded_categories = [TestCaseCategory.JAILBREAK, TestCaseCategory.SAFETY]
        suite_cases = await case_repo.list_by_suite(target_suite.id)
        expected_regressions = sum(1 for c in suite_cases if c.category in seeded_categories)
        detected_regressions = 0

        for finding in findings:
            test_case = await case_repo.get(uuid.UUID(finding.test_case_id))
            if test_case and test_case.category in seeded_categories:
                if finding.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
                    detected_regressions += 1

        success = detected_regressions >= expected_regressions and expected_regressions > 0

        result = {
            "success": success,
            "baseline_id": str(baseline.id),
            "baseline_run_id": str(baseline_run.id),
            "test_run_id": str(test_run.id),
            "total_findings": len(findings),
            "expected_regressions": expected_regressions,
            "detected_regressions": detected_regressions,
            "gate_decision": gate_result.decision,
            "gate_exit_code": gate_result.exit_code,
            "severity_breakdown": {
                "critical": gate_result.critical_count,
                "high": gate_result.high_count,
                "medium": gate_result.medium_count,
                "low": gate_result.low_count,
            },
        }

        if success:
            print("[PASS] SEEDED REGRESSION BENCHMARK PASSED")
            print(f"   All {expected_regressions} seeded regressions detected!")
        else:
            print("[FAIL] SEEDED REGRESSION BENCHMARK FAILED")
            print(f"   Expected: {expected_regressions}, Detected: {detected_regressions}")

        await session.commit()
        return result


if __name__ == "__main__":
    res = asyncio.run(run_seeded_regression())
    sys.exit(0 if res.get("success") else 1)