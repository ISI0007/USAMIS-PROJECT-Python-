"""Attendance records."""
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin, utcnow

ATTENDANCE_STATUSES = ("present", "absent", "excused", "late")


class Attendance(TimestampMixin, db.Model):
    """One attendance record per (student, offering, date) — enforced by a
    unique constraint to prevent duplicates."""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", "session_date",
                         name="uq_attendance_student_offering_date"),
        CheckConstraint(
            "status IN ('present','absent','excused','late')",
            name="ck_attendance_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="present")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student", back_populates="attendances")
    offering = relationship("CourseOffering")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Attendance s{self.student_id} {self.session_date} {self.status}>"
