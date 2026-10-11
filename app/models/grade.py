"""Grade records with explicit publication state and change auditing."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin


class Grade(TimestampMixin, db.Model):
    """A numeric grade (0-100) for one enrollment.

    Publication is modelled explicitly: unpublished grades are invisible to
    students and excluded from academic-performance calculations.
    """

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("enrollment_id", name="uq_grade_enrollment"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)",
                        name="ck_grade_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    letter: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    enrollment = relationship("Enrollment", back_populates="grade")
    student = relationship("Student", back_populates="grades")
    entered_by = relationship("User", foreign_keys=[entered_by_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Grade e{self.enrollment_id} {self.score}>"
