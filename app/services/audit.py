"""Audit-logging service.

Centralises writes to :class:`~app.models.user.AuditLog` so that every
sensitive action produces a consistent, safe record. Never stores passwords,
tokens, or unnecessary sensitive data.
"""
from flask import has_request_context, request
from flask_login import current_user

from ..extensions import db
from ..models import AuditLog


def _actor():
    if getattr(current_user, "is_authenticated", False):
        return current_user.id, current_user.username
    return None, "anonymous"


def _client_ip() -> str | None:
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.remote_addr or "")[:45] or None


def log_action(
    action: str,
    entity_type: str,
    entity_id=None,
    summary: str = "",
    actor=None,
    commit: bool = False,
) -> AuditLog:
    """Record an audit entry.

    :param actor: optional ``User`` overriding the current user (used by CLI
        seeding/tests).
    :param commit: when True the session is committed immediately.
    """
    if actor is not None:
        actor_id = actor.id
        actor_username = actor.username
    else:
        actor_id, actor_username = _actor()

    entry = AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary[:2000] if summary else "",
        ip_address=_client_ip(),
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
