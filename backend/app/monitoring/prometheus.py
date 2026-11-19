"""Prometheus metrics computed from the database at scrape time.

These are the series the Grafana dashboard (infra/grafana/dashboards/overview.json) queries.
Each scrape runs a handful of aggregate queries; nothing is cached or estimated, and a
value with no underlying data (e.g. pass rate with no runs in the last 24 hours) is left
out rather than reported as 0.
"""
from datetime import UTC, datetime, timedelta

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ReviewStatus, RunStatus, SeverityLevel
from app.models.review import ReviewQueue
from app.models.run import Run

DURATION_BUCKETS = (5, 15, 30, 60, 120, 300, 600, 1800, 3600)
OPEN_REVIEW = (ReviewStatus.PENDING, ReviewStatus.IN_REVIEW, ReviewStatus.ESCALATED)
SCORED_RUN = (RunStatus.COMPLETED, RunStatus.REVIEW_REQUIRED)


class _Snapshot:
    """A collector that yields metric families computed beforehand."""

    def __init__(self, families):
        self._families = families

    def collect(self):
        yield from self._families


async def render_metrics(session: AsyncSession) -> bytes:
    families = []

    runs = (await session.execute(select(func.count(Run.id)))).scalar_one()
    families.append(GaugeMetricFamily("redteam_runs_total", "Evaluation runs stored", value=runs))
    families.append(CounterMetricFamily("redteam_runs_created", "Evaluation runs created", value=runs))

    since = datetime.now(UTC) - timedelta(hours=24)
    passed, total = (
        await session.execute(
            select(func.coalesce(func.sum(Run.passed_count), 0), func.coalesce(func.sum(Run.total_tests), 0))
            .where(Run.status.in_(SCORED_RUN), Run.created_at >= since)
        )
    ).one()
    if total:
        families.append(
            GaugeMetricFamily(
                "redteam_pass_rate", "Share of passing tests in runs scored in the last 24 hours",
                value=passed / total,
            )
        )

    open_reviews = (
        await session.execute(select(func.count(ReviewQueue.id)).where(ReviewQueue.status.in_(OPEN_REVIEW)))
    ).scalar_one()
    open_regressions = (
        await session.execute(
            select(func.count(ReviewQueue.id)).where(
                ReviewQueue.status.in_(OPEN_REVIEW), ReviewQueue.regression_id.is_not(None)
            )
        )
    ).scalar_one()
    open_critical = (
        await session.execute(
            select(func.count(ReviewQueue.id)).where(
                ReviewQueue.status.in_(OPEN_REVIEW), ReviewQueue.severity == SeverityLevel.CRITICAL
            )
        )
    ).scalar_one()
    families.append(GaugeMetricFamily("redteam_review_queue_size", "Open review items", value=open_reviews))
    families.append(
        GaugeMetricFamily("redteam_regressions_active", "Regressions with an open review", value=open_regressions)
    )
    families.append(
        GaugeMetricFamily("redteam_critical_findings", "Open critical review items", value=open_critical)
    )

    cost = (await session.execute(select(func.coalesce(func.sum(Run.total_cost_usd), 0.0)))).scalar_one()
    families.append(CounterMetricFamily("redteam_cost_usd", "Evaluation cost in USD", value=float(cost)))

    rows = (
        await session.execute(
            select(Run.started_at, Run.completed_at).where(
                Run.started_at.is_not(None), Run.completed_at.is_not(None)
            )
        )
    ).all()
    durations = [max(0.0, (done - start).total_seconds()) for start, done in rows]
    buckets = [(str(b), sum(1 for d in durations if d <= b)) for b in DURATION_BUCKETS]
    buckets.append(("+Inf", len(durations)))
    families.append(
        HistogramMetricFamily(
            "redteam_run_duration_seconds", "Time from run start to completion",
            buckets=buckets, sum_value=sum(durations),
        )
    )

    registry = CollectorRegistry()
    registry.register(_Snapshot(families))
    return generate_latest(registry)
