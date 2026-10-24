from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TestCaseCategory
from app.models.test_suite import TestCase, TestCaseVersion, TestSuite, TestSuiteVersion
from app.repositories.base import BaseRepository


class TestSuiteRepository(BaseRepository[TestSuite]):
    def __init__(self, session: AsyncSession):
        super().__init__(TestSuite, session)

    async def get_by_name(self, name: str) -> TestSuite | None:
        result = await self.session.execute(select(TestSuite).where(TestSuite.name == name))
        return result.scalar_one_or_none()

    async def get_latest_version(self, suite_id: UUID) -> TestSuite | None:
        result = await self.session.execute(
            select(TestSuite).where(TestSuite.id == suite_id).order_by(TestSuite.version.desc())
        )
        return result.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[TestSuite]:
        return await self.list(skip=skip, limit=limit, filters={"is_active": True})


class TestSuiteVersionRepository(BaseRepository[TestSuiteVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(TestSuiteVersion, session)

    async def get_latest(self, suite_id: UUID) -> TestSuiteVersion | None:
        result = await self.session.execute(
            select(TestSuiteVersion)
            .where(TestSuiteVersion.suite_id == suite_id)
            .order_by(TestSuiteVersion.version.desc())
        )
        return result.scalar_one_or_none()


class TestCaseRepository(BaseRepository[TestCase]):
    def __init__(self, session: AsyncSession):
        super().__init__(TestCase, session)

    async def get_by_suite_and_id(self, suite_id: UUID, test_case_id: str) -> TestCase | None:
        result = await self.session.execute(
            select(TestCase).where(
                TestCase.suite_id == suite_id, TestCase.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_suite(
        self, suite_id: UUID, skip: int = 0, limit: int | None = None
    ) -> list[TestCase]:
        return await self.list(
            skip=skip, limit=limit, filters={"suite_id": suite_id, "is_active": True}
        )

    async def list_by_ids(self, ids: set[str]) -> list[TestCase]:
        """Fetch many test cases in a single query (avoids an N+1 pattern)."""
        if not ids:
            return []
        result = await self.session.execute(
            select(TestCase).where(TestCase.id.in_({str(i) for i in ids}))
        )
        return list(result.scalars().all())
    async def list_by_suite_ids(self, suite_ids: set[str]) -> list[TestCase]:
        """All active test cases of many suites, in a single query."""
        if not suite_ids:
            return []
        result = await self.session.execute(
            select(TestCase).where(
                TestCase.suite_id.in_({str(s) for s in suite_ids}),
                TestCase.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_all_by_suite(self, suite_id: UUID) -> list[TestCase]:
        """Every active test case of a suite, without the default page limit.

        The evaluation pipeline must score every test case in the suite; the
        paginated ``list_by_suite`` silently truncated the run at 100 cases.
        """
        result = await self.session.execute(
            select(TestCase)
            .where(TestCase.suite_id == suite_id, TestCase.is_active.is_(True))
            .order_by(TestCase.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_by_category(self, suite_id: UUID, category: TestCaseCategory) -> list[TestCase]:
        return await self.list(
            filters={"suite_id": suite_id, "category": category, "is_active": True}
        )

    async def count_by_suite(self, suite_id: UUID) -> int:
        return await self.count(filters={"suite_id": suite_id, "is_active": True})


class TestCaseVersionRepository(BaseRepository[TestCaseVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(TestCaseVersion, session)

    async def get_latest(self, test_case_id: UUID) -> TestCaseVersion | None:
        result = await self.session.execute(
            select(TestCaseVersion)
            .where(TestCaseVersion.test_case_id == test_case_id)
            .order_by(TestCaseVersion.version.desc())
        )
        return result.scalar_one_or_none()
