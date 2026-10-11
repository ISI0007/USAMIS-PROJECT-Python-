"""Outbound SMS notification records.

Messages are composed and persisted here, then handed to an :class:`SmsProvider`
adapter. In development the adapter is a stub that records the send instead of
calling any network, so the feature is fully exercisable offline.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin

SMS_STATUSES = ("queued", "sent", "failed")
SMS_CATEGORIES = ("fee_reminder", "payment_received", "account", "general")


class SmsMessage(TimestampMixin, db.Model):
    """One outbound SMS message."""

    __tablename__ = "sms_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(24), nullable=False, default="general", index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued", index=True
    )
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SmsMessage {self.recipient} {self.status}>"
