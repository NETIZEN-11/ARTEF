from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ExecutionStatus, RunStatus, Verdict
from app.models.run import Execution, Result, Run
from app.models.target_agent import TargetAgent
from app.models.test_suite import TestSuite
from app.repositories.base import BaseRepository


class RunRepository(BaseRepository[Run]):
    def __init__(self, session: AsyncSession):
        super().__init__(Run, session)

    # The scalar columns of a run. The ``runs`` table declares four
    # relationships with ``lazy="joined"``, so a plain ``select(Run)``
    # joins ten tables and materialises every related row. The list
    # endpoints only need the run counters, so they select these columns
    # instead.
    LIST_COLUMNS = (
        Run.id,
        Run.target_agent_id,
        Run.suite_id,
        Run.suite_version,
        Run.baseline_id,
        Run.matrix_id,
        Run.status,
        Run.framework_version,
        Run.started_at,
        Run.completed_at,
        Run.total_tests,
        Run.passed_count,
        Run.failed_count,
        Run.inconclusive_count,
        Run.regression_count,
        Run.critical_count,
        Run.high_count,
        Run.medium_count,
        Run.low_count,
        Run.total_cost_usd,
        Run.total_latency_ms,
        Run.error_message,
        Run.gate_decision,
        Run.created_at,
        Run.updated_at,
    )

    async def list_scalars(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict]:
        """List runs without loading the related rows.

        Returns the run counters as plain dictionaries. Only the agent and suite
        names are joined in (for display); the baseline, matrix and other related
        rows are not loaded.
        """
        columns = [
            *self.LIST_COLUMNS,
            TargetAgent.name.label("target_agent_name"),
            TestSuite.name.label("suite_name"),
        ]
        query = (
            select(*columns)
            .outerjoin(TargetAgent, TargetAgent.id == Run.target_agent_id)
            .outerjoin(TestSuite, TestSuite.id == Run.suite_id)
        )
        if filters:
            for field, value in filters.items():
                query = query.where(self._column(field) == value)
        if order_by:
            column = self._column(order_by)
            query = query.order_by(column.desc() if descending else column.asc())
        else:
            # Newest first; the id breaks ties so pagination is stable.
            query = query.order_by(Run.created_at.desc(), Run.id.asc())
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return [dict(row._mapping) for row in result.all()]

    async def list_scalars_since(
        self,
        since: datetime,
        limit: int = 50000,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict]:
        """List the run counters of every run created at or after ``since``.

        The filter is applied in SQL so that the number of rows that reach
        Python depends on the requested time range and not on the size of
        the table.
        """
        query = select(*self.LIST_COLUMNS).where(self._column("created_at") >= since)
        if order_by:
            column = self._column(order_by)
            query = query.order_by(column.desc() if descending else column.asc())
        else:
            query = query.order_by(self._column("id").asc())
        query = query.limit(limit)
        result = await self.session.execute(query)
        return [dict(row._mapping) for row in result.all()]

    async def list_by_agent(self, agent_id: UUID, skip: int = 0, limit: int = 100) -> list[Run]:
        return await self.list(skip=skip, limit=limit, filters={"target_agent_id": agent_id})

    async def list_by_suite(self, suite_id: UUID, skip: int = 0, limit: int = 100) -> list[Run]:
        return await self.list(skip=skip, limit=limit, filters={"suite_id": suite_id})

    async def list_by_status(self, status: RunStatus, skip: int = 0, limit: int = 100) -> list[Run]:
        return await self.list(skip=skip, limit=limit, filters={"status": status})

    async def get_latest_for_agent_suite(self, agent_id: UUID, suite_id: UUID) -> Run | None:
        result = await self.session.execute(
            select(Run)
            .where(Run.target_agent_id == agent_id, Run.suite_id == suite_id)
            .order_by(Run.created_at.desc())
        )
        return result.scalars().first()

    async def aggregate_stats(self) -> dict:
        """Aggregate the run counters in SQL.

        The previous implementation loaded 200 fully-hydrated ``Run`` rows -
        each with four ``lazy="joined"`` relationships, so 200 rows meant
        800 JOINed rows - and summed the counters in Python. This performs a
        single ``GROUP BY`` aggregate instead.
        """
        stmt = select(
            func.count(Run.id),
            func.coalesce(func.sum(Run.total_tests), 0),
            func.coalesce(func.sum(Run.passed_count), 0),
            func.coalesce(func.sum(Run.failed_count), 0),
            func.coalesce(func.sum(Run.inconclusive_count), 0),
            func.coalesce(func.sum(Run.regression_count), 0),
            func.coalesce(func.sum(Run.critical_count), 0),
            func.coalesce(func.sum(Run.high_count), 0),
            func.coalesce(func.sum(Run.medium_count), 0),
            func.coalesce(func.sum(Run.low_count), 0),
            func.coalesce(func.sum(Run.total_latency_ms), 0),
            func.coalesce(func.sum(Run.total_cost_usd), 0.0),
        )
        row = (await self.session.execute(stmt)).one()
        return {
            "total_runs": row[0] or 0,
            "total_tests": row[1] or 0,
            "passed": row[2] or 0,
            "failed": row[3] or 0,
            "inconclusive": row[4] or 0,
            "regressions": row[5] or 0,
            "critical": row[6] or 0,
            "high": row[7] or 0,
            "medium": row[8] or 0,
            "low": row[9] or 0,
            "total_latency": row[10] or 0,
            "total_cost": float(row[11] or 0.0),
        }

    async def list_completed_trend(self, limit: int = 7) -> list[Run]:
        """The most recent completed runs, used for the trend charts.

        Only the three counters that the trend charts need are selected, so
        the query does not join the ten related tables that a full ``Run``
        row would pull in.
        """
        stmt = (
            select(
                Run.id,
                Run.total_tests,
                Run.passed_count,
                Run.regression_count,
                Run.total_cost_usd,
            )
            .where(Run.status == RunStatus.COMPLETED)
            .order_by(Run.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(reversed(result.all()))


class ExecutionRepository(BaseRepository[Execution]):
    def __init__(self, session: AsyncSession):
        super().__init__(Execution, session)

    async def list_by_run(self, run_id: UUID, skip: int = 0, limit: int | None = None) -> list[Execution]:
        return await self.list(skip=skip, limit=limit, filters={"run_id": run_id})

    async def list_all_by_run(self, run_id: UUID) -> list[Execution]:
        """Every execution of a run, without the default page limit.

        Scoring must process every execution; the paginated ``list_by_run``
        silently stopped at 100 executions while the run reported the full
        test count.
        """
        result = await self.session.execute(
            select(Execution)
            .where(Execution.run_id == run_id)
            .order_by(Execution.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_run_and_test_case(self, run_id: UUID, test_case_id: UUID) -> Execution | None:
        result = await self.session.execute(
            select(Execution).where(
                Execution.run_id == run_id, Execution.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()

    async def count_by_run_and_status(self, run_id: UUID, status: ExecutionStatus) -> int:
        return await self.count(filters={"run_id": run_id, "status": status})


class ResultRepository(BaseRepository[Result]):
    def __init__(self, session: AsyncSession):
        super().__init__(Result, session)

    async def list_by_run(
        self, run_id: UUID | str, skip: int = 0, limit: int | None = None
    ) -> list[Result]:
        return await self.list(skip=skip, limit=limit, filters={"run_id": run_id})

    async def list_all_by_run(self, run_id: UUID | str) -> list[Result]:
        """Every result of a run, without the default page limit."""
        result = await self.session.execute(
            select(Result).where(Result.run_id == run_id).order_by(Result.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_by_run_and_verdict(self, run_id: UUID, verdict: Verdict) -> list[Result]:
        return await self.list(filters={"run_id": run_id, "verdict": verdict})

    async def get_by_run_and_test_case(self, run_id: UUID | str, test_case_id: UUID | str) -> Result | None:
        result = await self.session.execute(
            select(Result).where(Result.run_id == run_id, Result.test_case_id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def count_by_run_and_verdict(self, run_id: UUID, verdict: Verdict) -> int:
        return await self.count(filters={"run_id": run_id, "verdict": verdict})

    async def get_run_stats(self, run_id: UUID) -> dict:
        total = await self.count(filters={"run_id": run_id})
        passed = await self.count(filters={"run_id": run_id, "verdict": Verdict.PASS})
        failed = await self.count(filters={"run_id": run_id, "verdict": Verdict.FAIL})
        inconclusive = await self.count(filters={"run_id": run_id, "verdict": Verdict.INCONCLUSIVE})
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
        }
