from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import TokenData, get_result_repo, get_run_repo, require_role
from app.domain.enums import Verdict
from app.models.run import Result, Run
from app.models.test_suite import TestCase
from app.repositories.runs import ResultRepository, RunRepository

router = APIRouter()


class DateCount(BaseModel):
    date: str
    count: int


class DateRate(BaseModel):
    date: str
    rate: float


class DateCost(BaseModel):
    date: str
    cost: float


class DateLatency(BaseModel):
    date: str
    latency: float


class NameCount(BaseModel):
    severity: str | None = None
    category: str | None = None
    count: int


class FailingTest(BaseModel):
    test_case_id: str
    failure_count: int


class AnalyticsResponse(BaseModel):
    runs_over_time: list[dict[str, Any]]
    pass_rate_over_time: list[dict[str, Any]]
    regressions_over_time: list[dict[str, Any]]
    cost_over_time: list[dict[str, Any]]
    latency_over_time: list[dict[str, Any]]
    severity_distribution: list[dict[str, Any]]
    category_distribution: list[dict[str, Any]]
    top_failing_tests: list[dict[str, Any]]


@router.get("", response_model=AnalyticsResponse)
@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    time_range: str = Query("7d", alias="range", pattern="^(24h|7d|30d|90d|1y)$"),
    run_repo: RunRepository = Depends(get_run_repo),
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    days_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = days_map.get(time_range, 7)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # The date filter is applied in SQL and only the counter columns are
    # selected. The previous implementation loaded up to 5000 fully-hydrated
    # ``Run`` rows - each joining ten related tables - and filtered them in
    # Python, so the "range" parameter did not actually restrict the result
    # set and the response time grew with the size of the table.
    filtered_runs = await run_repo.list_scalars_since(
        cutoff, limit=50000, order_by="created_at", descending=True
    )

    runs_by_day: dict[str, int] = defaultdict(int)
    passed_by_day: dict[str, int] = defaultdict(int)
    tests_by_day: dict[str, int] = defaultdict(int)
    regressions_by_day: dict[str, int] = defaultdict(int)
    cost_by_day: dict[str, float] = defaultdict(float)
    latency_by_day: dict[str, list[int]] = defaultdict(list)

    total_critical = 0
    total_high = 0
    total_medium = 0
    total_low = 0

    for r in filtered_runs:
        day_str = _as_utc(r["created_at"]).strftime("%Y-%m-%d")
        runs_by_day[day_str] += 1
        tests_by_day[day_str] += r["total_tests"] or 0
        passed_by_day[day_str] += r["passed_count"] or 0
        regressions_by_day[day_str] += r["regression_count"] or 0
        cost_by_day[day_str] += r["total_cost_usd"] or 0.0
        if r["total_latency_ms"]:
            latency_by_day[day_str].append(r["total_latency_ms"])

        total_critical += r["critical_count"] or 0
        total_high += r["high_count"] or 0
        total_medium += r["medium_count"] or 0
        total_low += r["low_count"] or 0

    sorted_days = sorted(runs_by_day.keys())
    if not sorted_days:
        for i in range(min(days, 7), -1, -1):
            d = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            sorted_days.append(d)

    runs_over_time = [{"date": d, "count": runs_by_day.get(d, 0)} for d in sorted_days]
    # Only days that actually ran tests; an empty day is not a 100% pass rate.
    pass_rate_over_time = [
        {"date": d, "rate": round(passed_by_day[d] / tests_by_day[d] * 100, 1)}
        for d in sorted_days
        if tests_by_day.get(d, 0) > 0
    ]
    regressions_over_time = [
        {"date": d, "count": regressions_by_day.get(d, 0)} for d in sorted_days
    ]
    cost_over_time = [
        {"date": d, "cost": round(cost_by_day.get(d, 0.0), 3)} for d in sorted_days
    ]
    latency_over_time = [
        {
            "date": d,
            "latency": round(
                (sum(latency_by_day[d]) / len(latency_by_day[d])) if latency_by_day.get(d) else 0.0,
                1,
            ),
        }
        for d in sorted_days
    ]

    severity_distribution = [
        {"severity": "Critical", "count": total_critical},
        {"severity": "High", "count": total_high},
        {"severity": "Medium", "count": total_medium},
        {"severity": "Low", "count": total_low},
    ]

    run_ids = [str(r["id"]) for r in filtered_runs]
    category_distribution, top_failing_tests = await _failure_breakdown(
        result_repo, run_ids, days
    )

    return AnalyticsResponse(
        runs_over_time=runs_over_time,
        pass_rate_over_time=pass_rate_over_time,
        regressions_over_time=regressions_over_time,
        cost_over_time=cost_over_time,
        latency_over_time=latency_over_time,
        severity_distribution=severity_distribution,
        category_distribution=category_distribution,
        top_failing_tests=top_failing_tests,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _failure_breakdown(
    result_repo: ResultRepository, run_ids: list[str], days: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Aggregate real failures by test-case category and by test case.

    Both breakdowns are derived from the ``results`` table joined to
    ``test_cases``; nothing here is synthesised from severity counters.
    """
    if not run_ids:
        return [], []

    session = result_repo.session
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # The run ids are matched with a subquery on ``created_at`` rather than
    # with a literal ``IN`` list. A range of a year can contain tens of
    # thousands of run ids, and embedding them all in the statement made the
    # query plan and the parameter list grow without bound.
    recent_run_ids = select(Run.id).where(Run.created_at >= cutoff)

    category_rows = await session.execute(
        select(TestCase.category, func.count(Result.id))
        .join(Result, Result.test_case_id == TestCase.id)
        .where(
            Result.run_id.in_(recent_run_ids),
            Result.verdict == Verdict.FAIL,
            Result.created_at >= cutoff,
        )
        .group_by(TestCase.category)
        .order_by(func.count(Result.id).desc())
    )
    category_distribution = [
        {
            "category": (category.value if hasattr(category, "value") else str(category))
            .replace("_", " ")
            .title(),
            "count": count,
        }
        for category, count in category_rows.all()
    ]

    # Report the suite's own test id (e.g. "JB_001"), not the internal primary key.
    failing_rows = await session.execute(
        select(TestCase.test_case_id, func.count(Result.id))
        .join(Result, Result.test_case_id == TestCase.id)
        .where(
            Result.run_id.in_(recent_run_ids),
            Result.verdict == Verdict.FAIL,
            Result.created_at >= cutoff,
        )
        .group_by(TestCase.id, TestCase.test_case_id)
        .order_by(func.count(Result.id).desc())
        .limit(10)
    )
    top_failing_tests = [
        {"test_case_id": str(test_case_id), "failure_count": count}
        for test_case_id, count in failing_rows.all()
    ]

    return category_distribution, top_failing_tests
