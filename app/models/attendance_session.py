"""QR-code attendance sessions (F3).

A teacher opens a session for a course offering; the app renders a signed,
time-limited token as a QR code. A student scans it, and — if enrolled — the
token marks their attendance as ``present`` with ``source='qr'``.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin, utcnow


class AttendanceSession(TimestampMixin, db.Model):
    """One QR attendance session for a course offering on a given date."""

    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    opened_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    offering = relationship("CourseOffering")
    records = relationship("Attendance", back_populates="session")

    def is_expired(self) -> bool:
        # Normalise to naive UTC for comparison: SQLite/psycopg may return naive
        expires = self.expires_at
        return datetime.utcnow() > (expires.replace(tzinfo=None) if expires.tzinfo else expires)

    def is_active(self) -> bool:
        return self.is_open and not self.is_expired()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AttendanceSession o{self.offering_id} {self.session_date:%Y-%m-%d}>"
