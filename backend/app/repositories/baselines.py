from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ReviewStatus, SeverityLevel
from app.models.audit_log import AuditLog
from app.models.baseline import Baseline, BaselineItem
from app.models.regression import Regression, SeverityFinding
from app.models.review import ReviewLabelRecord, ReviewQueue
from app.repositories.base import BaseRepository


class BaselineRepository(BaseRepository[Baseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(Baseline, session)

    async def get_active_for_suite(self, suite_id: UUID) -> Baseline | None:
        # Most recently approved active baseline (create_baseline keeps at most one active,
        # but never crash on legacy data with several).
        result = await self.session.execute(
            select(Baseline)
            .where(Baseline.suite_id == suite_id, Baseline.is_active.is_(True))
            .order_by(Baseline.approved_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_by_suite_version(self, suite_id: UUID, suite_version: int) -> Baseline | None:
        result = await self.session.execute(
            select(Baseline)
            .where(
                Baseline.suite_id == suite_id, Baseline.suite_version == suite_version
            )
            .order_by(Baseline.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_by_run(self, run_id: UUID) -> Baseline | None:
        result = await self.session.execute(select(Baseline).where(Baseline.run_id == run_id))
        return result.scalars().first()

    async def deactivate_for_suite(self, suite_id: UUID, keep_id: UUID | None = None) -> None:
        for baseline in await self.list(limit=None, filters={"suite_id": suite_id, "is_active": True}):
            if keep_id is None or str(baseline.id) != str(keep_id):
                baseline.is_active = False
        await self.session.flush()

    async def list_by_suite(self, suite_id: UUID) -> list[Baseline]:
        return await self.list(filters={"suite_id": suite_id})


class BaselineItemRepository(BaseRepository[BaselineItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(BaselineItem, session)

    async def list_by_baseline(self, baseline_id: UUID) -> list[BaselineItem]:
        return await self.list(limit=None, filters={"baseline_id": baseline_id})

    async def get_by_baseline_and_test_case(
        self, baseline_id: UUID | str, test_case_id: UUID | str
    ) -> BaselineItem | None:
        result = await self.session.execute(
            select(BaselineItem).where(
                BaselineItem.baseline_id == baseline_id, BaselineItem.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()


class RegressionRepository(BaseRepository[Regression]):
    def __init__(self, session: AsyncSession):
        super().__init__(Regression, session)

    async def list_by_run(self, run_id: UUID) -> list[Regression]:
        return await self.list(limit=None, filters={"run_id": run_id})

    async def list_by_baseline(self, baseline_id: UUID) -> list[Regression]:
        return await self.list(limit=None, filters={"baseline_id": baseline_id})

    async def list_by_severity(self, severity: SeverityLevel) -> list[Regression]:
        return await self.list(filters={"severity": severity})

    async def get_by_run_and_test_case(
        self, run_id: UUID | str, test_case_id: UUID | str
    ) -> Regression | None:
        result = await self.session.execute(
            select(Regression).where(
                Regression.run_id == run_id, Regression.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()


class SeverityFindingRepository(BaseRepository[SeverityFinding]):
    def __init__(self, session: AsyncSession):
        super().__init__(SeverityFinding, session)

    async def get_by_regression(self, regression_id: UUID) -> SeverityFinding | None:
        result = await self.session.execute(
            select(SeverityFinding).where(SeverityFinding.regression_id == regression_id)
        )
        return result.scalar_one_or_none()


class ReviewQueueRepository(BaseRepository[ReviewQueue]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewQueue, session)

    async def list_pending(self, skip: int = 0, limit: int = 100) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"status": ReviewStatus.PENDING})

    async def count_pending(self) -> int:
        return await self.count(filters={"status": ReviewStatus.PENDING})

    async def list_by_status(
        self, status: ReviewStatus, skip: int = 0, limit: int = 100
    ) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"status": status})

    async def list_by_assignee(
        self, assignee_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"assigned_to": assignee_id})

    async def get_by_regression(self, regression_id: UUID | str) -> ReviewQueue | None:
        result = await self.session.execute(
            select(ReviewQueue).where(ReviewQueue.regression_id == regression_id)
        )
        return result.scalars().first()

    async def create_review(
        self,
        regression_id: UUID | str,
        run_id: UUID | str,
        severity: SeverityLevel,
        confidence: float,
        category: str,
    ) -> ReviewQueue:
        """Create a pending review entry for a regression finding.

        Idempotent: a regression may only appear once in the review queue
        (``uq_review_regression``), so an existing entry is returned instead of
        raising an IntegrityError.
        """
        existing = await self.get_by_regression(str(regression_id))
        if existing:
            return existing

        review = ReviewQueue(
            regression_id=str(regression_id),
            run_id=str(run_id),
            severity=severity,
            confidence=confidence,
            category=category,
            status=ReviewStatus.PENDING,
        )
        return await self.create(review)


class ReviewLabelRepository(BaseRepository[ReviewLabelRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewLabelRecord, session)

    async def list_by_review(self, review_id: UUID) -> list[ReviewLabelRecord]:
        return await self.list(filters={"review_id": review_id})

    async def get_latest_by_review(self, review_id: UUID) -> ReviewLabelRecord | None:
        result = await self.session.execute(
            select(ReviewLabelRecord)
            .where(ReviewLabelRecord.review_id == review_id)
            .order_by(ReviewLabelRecord.created_at.desc())
        )
        return result.scalar_one_or_none()


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        return await self.list(skip=skip, limit=limit, filters={"user_id": user_id})

    async def list_by_resource(self, resource_type: str, resource_id: UUID) -> list[AuditLog]:
        return await self.list(filters={"resource_type": resource_type, "resource_id": resource_id})

    async def list_by_action(self, action: str, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        return await self.list(skip=skip, limit=limit, filters={"action": action})
