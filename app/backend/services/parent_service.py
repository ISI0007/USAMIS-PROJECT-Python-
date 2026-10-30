"""Parent-portal service (F5).

Resolves which students a parent account may see and assembles their records.
Authorization is enforced here *and* in the route decorator: a parent can only
ever reach students linked to their own account.
"""
from __future__ import annotations

from ..extensions import db
from ..models import ParentLink, Student


def linked_students(parent_user) -> list[Student]:
    """Return the active students linked to ``parent_user`` (never others')."""
    rows = db.session.execute(
        db.select(Student)
        .join(ParentLink, ParentLink.student_id == Student.id)
        .where(
            ParentLink.parent_user_id == parent_user.id,
            ParentLink.is_active.is_(True),
        )
        .order_by(Student.student_number)
    ).scalars().all()
    return list(rows)


def link_for(parent_user, student: Student) -> ParentLink | None:
    """Return the active link row, or ``None`` when the parent may not see this
    student. This is the single ownership guard used by the detail routes."""
    return db.session.execute(
        db.select(ParentLink).where(
            ParentLink.parent_user_id == parent_user.id,
            ParentLink.student_id == student.id,
            ParentLink.is_active.is_(True),
        )
    ).scalars().first()


def relationship_label(value: str) -> str:
    return {
        "father": "Father",
        "mother": "Mother",
        "guardian": "Guardian",
        "other": "Other",
    }.get(value, value.title() if value else "")
