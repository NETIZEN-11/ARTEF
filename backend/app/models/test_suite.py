from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ExpectedBehaviorType, TestCaseCategory, TestCaseSeverity
from app.models.types import UUIDString
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.baseline import Baseline, BaselineItem
    from app.models.dataset import Dataset
    from app.models.matrix import EvaluationMatrix
    from app.models.run import Execution, Result, Run


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dataset_id: Mapped[String | None] = mapped_column(
        UUIDString(), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="suite", lazy="dynamic", cascade="all, delete-orphan"
    )
    versions: Mapped[list["TestSuiteVersion"]] = relationship(
        back_populates="suite", lazy="dynamic", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(back_populates="suite", lazy="dynamic")
    baselines: Mapped[list["Baseline"]] = relationship(back_populates="suite", lazy="dynamic")
    matrices: Mapped[list["EvaluationMatrix"]] = relationship(back_populates="suite", lazy="dynamic")
    dataset: Mapped["Dataset"] = relationship(back_populates="test_suites", lazy="joined")

    __table_args__ = (
        Index("ix_test_suites_name_version", "name", "version"),
        UniqueConstraint("name", "version", name="uq_test_suite_name_version"),
    )


class TestSuiteVersion(Base):
    __tablename__ = "test_suite_versions"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[String] = mapped_column(
        UUIDString(),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="versions", lazy="joined")

    __table_args__ = (UniqueConstraint("suite_id", "version", name="uq_test_suite_version"),)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[String] = mapped_column(
        UUIDString(),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[TestCaseCategory] = mapped_column(
        SQLEnum(TestCaseCategory, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    severity: Mapped[TestCaseSeverity] = mapped_column(
        SQLEnum(TestCaseSeverity, native_enum=False, create_constraint=True),
        nullable=False,
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior_type: Mapped[ExpectedBehaviorType] = mapped_column(
        SQLEnum(ExpectedBehaviorType, native_enum=False, create_constraint=True),
        nullable=False,
    )
    matcher_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rubric_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    test_case_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="test_cases", lazy="joined")
    versions: Mapped[list["TestCaseVersion"]] = relationship(
        back_populates="test_case", lazy="dynamic", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(back_populates="test_case", lazy="dynamic")
    results: Mapped[list["Result"]] = relationship(back_populates="test_case", lazy="dynamic")
    baseline_items: Mapped[list["BaselineItem"]] = relationship(
        back_populates="test_case", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(
            "suite_id", "test_case_id", "version", name="uq_test_case_suite_id_version"
        ),
        Index("ix_test_cases_suite_category", "suite_id", "category"),
    )

    def __init__(self, **kwargs: Any) -> None:
        # ``metadata`` is a reserved SQLAlchemy attribute (Base.metadata), so the
        # mapped column is exposed as ``test_case_metadata``. Accept the plain
        # ``metadata=`` keyword used by the API/service layer and translate it.
        if "metadata" in kwargs:
            value = kwargs.pop("metadata")
            if value is not None and not isinstance(value, dict):
                value = value.model_dump() if hasattr(value, "model_dump") else dict(value)
            kwargs["test_case_metadata"] = value
        super().__init__(**kwargs)

    @property
    def expected_behavior(self) -> dict[str, Any]:
        """Composite view over the split expected_behavior_* columns.

        The behaviour is stored as three columns (type + matcher + rubric);
        this property reassembles them in the shape suites are submitted in
        (empty matcher/rubric omitted, so the value can be posted back as-is).
        """
        behavior: dict[str, Any] = {
            "type": (
                self.expected_behavior_type.value
                if hasattr(self.expected_behavior_type, "value")
                else self.expected_behavior_type
            )
        }
        if self.matcher_config:
            behavior["matcher"] = self.matcher_config
        if self.rubric_config:
            behavior["rubric"] = self.rubric_config
        return behavior

    @expected_behavior.setter
    def expected_behavior(self, value: Any) -> None:
        """Persist an ExpectedBehavior value object into the split columns."""
        if value is None:
            return
        if isinstance(value, dict):
            data = value
            behavior_type = data.get("type")
            matcher = data.get("matcher", data.get("matcher_config"))
            rubric = data.get("rubric", data.get("rubric_config"))
        else:
            behavior_type = getattr(value, "type", None)
            matcher = getattr(value, "matcher", None)
            rubric = getattr(value, "rubric", None)

        if behavior_type is not None:
            self.expected_behavior_type = ExpectedBehaviorType(behavior_type)
        self.matcher_config = (
            matcher.model_dump() if hasattr(matcher, "model_dump") else matcher
        )
        self.rubric_config = (
            rubric.model_dump() if hasattr(rubric, "model_dump") else rubric
        )


class TestCaseVersion(Base):
    __tablename__ = "test_case_versions"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    test_case_id: Mapped[String] = mapped_column(
        UUIDString(),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    test_case: Mapped["TestCase"] = relationship(back_populates="versions", lazy="joined")

    __table_args__ = (UniqueConstraint("test_case_id", "version", name="uq_test_case_version"),)
