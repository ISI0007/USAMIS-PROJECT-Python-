"""User accounts, authentication state, and audit logging."""
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..security.permissions import Role, permissions_for, role_has_permission
from .mixins import TimestampMixin, utcnow


class User(UserMixin, TimestampMixin, db.Model):
    """An authenticated account with exactly one role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.STUDENT)
    is_active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Account lifecycle: active | inactive | blocked
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="user", uselist=False)
    teacher = relationship("Teacher", back_populates="user", uselist=False)

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #
    def set_password(self, password: str) -> None:
        """Hash and store a password using Werkzeug's secure default."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        """Flask-Login hook: inactive or blocked accounts cannot authenticate."""
        return self.is_active_flag and self.status == "active"

    # ------------------------------------------------------------------ #
    # Authorization
    # ------------------------------------------------------------------ #
    @property
    def role_label(self) -> str:
        from ..security.permissions import ROLE_LABELS

        return ROLE_LABELS.get(self.role, self.role)

    def has_permission(self, permission: str) -> bool:
        return role_has_permission(self.role, permission)

    @property
    def permissions(self) -> set[str]:
        return permissions_for(self.role)

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > utcnow())

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.username} ({self.role})>"


class AuditLog(db.Model):
    """Immutable record of security- and record-relevant actions.

    Never stores passwords, session secrets, or unnecessary sensitive data.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_username: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AuditLog {self.action} {self.entity_type}#{self.entity_id}>"
