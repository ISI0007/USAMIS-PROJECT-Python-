"""Parent/guardian links: a ``parent`` user watching one or more students.

F5 — parent portal. A parent account is read-only and may only see the
records of students explicitly linked to it. The link is a separate table
(not a column on ``users``) because one parent may have several children and
one student may have several guardians.
"""
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin

#: Relationship of the parent to the student (display only).
PARENT_RELATIONSHIPS = ("father", "mother", "guardian", "other")


class ParentLink(TimestampMixin, db.Model):
    """Links a parent user account to a student.

    Uniqueness is enforced on ``(parent_user_id, student_id)`` so a guardian
    cannot be linked to the same child twice. A student may still have several
    guardians (multiple rows with different ``parent_user_id``).
    """

    __tablename__ = "parent_links"
    __table_args__ = (
        UniqueConstraint("parent_user_id", "student_id",
                         name="uq_parent_link_user_student"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="guardian"
    )
    # Optional contact override; falls back to the user's own email/phone.
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        db.Boolean, nullable=False, default=True, server_default="true"
    )

    parent = relationship("User", foreign_keys=[parent_user_id])
    student = relationship("Student", foreign_keys=[student_id])

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ParentLink u{self.parent_user_id} s{self.student_id}>"
