"""Enrollment records linking students to course offerings."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin, utcnow

ENROLLMENT_STATUSES = ("pending", "enrolled", "rejected", "dropped", "completed")


class Enrollment(TimestampMixin, db.Model):
    """A student's registration in a course offering.

    Duplicate active enrollment in the same offering is prevented by a
    database unique constraint plus an application-level check.
    """

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", "status",
                         name="uq_enrollment_student_offering_status"),
        # Business rule: a student may hold at most one *active* enrollment per
        # offering. Rejected/dropped rows are kept as immutable history, so this
        # is a partial unique index over the active statuses only.
        Index(
            "uq_active_enrollment_student_offering",
            "student_id",
            "offering_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'enrolled', 'completed')"),
        ),
        CheckConstraint(
            "status IN ('pending','enrolled','rejected','dropped','completed')",
            name="ck_enrollment_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    student = relationship("Student", back_populates="enrollments")
    offering = relationship("CourseOffering", back_populates="enrollments")
    grade = relationship("Grade", back_populates="enrollment", uselist=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Enrollment s{self.student_id} o{self.offering_id} {self.status}>"
