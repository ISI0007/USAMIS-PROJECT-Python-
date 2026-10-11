"""Enrollment business rules.

Wraps Algorithm 1 (:mod:`app.algorithms.enrollment_eligibility`) with the
transaction/concurrency handling needed to be safe under simultaneous
requests, and records audit entries.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from ..algorithms.enrollment_eligibility import (
    REASON_ALREADY_ENROLLED,
    REASON_CAPACITY_FULL,
    EligibilityResult,
    check_capacity,
    evaluate_enrollment,
)
from ..extensions import db
from ..models import CourseOffering, Enrollment, Student
from ..models.mixins import utcnow
from . import audit


def evaluate(student: Student | None, offering: CourseOffering | None) -> EligibilityResult:
    """Read-only eligibility check (no writes)."""
    return evaluate_enrollment(student, offering, lock_capacity=False)


def _locked_offering(offering_id: int) -> CourseOffering:
    """Fetch an offering with a row lock (FOR UPDATE on PostgreSQL)."""
    return db.session.execute(
        db.select(CourseOffering)
        .where(CourseOffering.id == offering_id)
        .with_for_update()
    ).scalar_one()


def request_enrollment(student: Student, offering: CourseOffering, *, auto_approve: bool = False):
    """Create an enrollment request for ``student``.

    Runs the eligibility algorithm, then rechecks capacity inside a locked
    transaction before inserting. Returns ``(enrollment | None, result)``.

    Concurrency: the offering row is locked ``FOR UPDATE`` on PostgreSQL so
    the capacity check and the insert are atomic with respect to other
    enrollment transactions.
    """
    # Cheap pre-check outside the lock for a friendly early rejection.
    pre = evaluate_enrollment(student, offering, lock_capacity=False)
    if not pre.eligible:
        return None, pre

    try:
        locked_offering = _locked_offering(offering.id)

        has_room, enrolled, capacity = check_capacity(locked_offering, lock=False)
        if not has_room:
            db.session.rollback()
            return None, EligibilityResult(
                False,
                REASON_CAPACITY_FULL,
                f"Course is full ({enrolled}/{capacity}).",
                details={"enrolled": enrolled, "capacity": capacity},
            )

        # Re-evaluate under the lock (duplicate/capacity could have changed).
        locked = evaluate_enrollment(student, locked_offering, lock_capacity=False)
        if not locked.eligible:
            db.session.rollback()
            return None, locked

        enrollment = Enrollment(
            student_id=student.id,
            offering_id=locked_offering.id,
            status="enrolled" if auto_approve else "pending",
            eligibility_reason=locked.message,
        )
        db.session.add(enrollment)
        db.session.flush()

        audit.log_action(
            "enrollment_request" if not auto_approve else "enrollment_approved",
            "Enrollment",
            enrollment.id,
            summary=(
                f"Student {student.student_number} -> {locked_offering.course.code} "
                f"({locked_offering.semester.label})"
            ),
        )
        db.session.commit()
        return enrollment, locked
    except IntegrityError:
        db.session.rollback()
        return None, EligibilityResult(
            False, REASON_ALREADY_ENROLLED, "A duplicate enrollment already exists."
        )


def decide(actor, enrollment_id: int, approve: bool, note: str = ""):
    """Approve or reject a pending enrollment request.

    Returns the updated :class:`Enrollment`, or ``None`` when the request is
    missing or not pending, or when approving would exceed capacity.
    """
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None or enrollment.status != "pending":
        return None

    if approve:
        offering = _locked_offering(enrollment.offering_id)
        has_room, enrolled, capacity = check_capacity(offering, lock=False)
        if not has_room:
            db.session.rollback()
            return None
        enrollment.status = "enrolled"
        enrollment.eligibility_reason = f"Approved ({enrolled}/{capacity} seats used)."
        action = "enrollment_approved"
    else:
        enrollment.status = "rejected"
        action = "enrollment_rejected"

    enrollment.decided_by_id = actor.id
    enrollment.decided_at = utcnow()
    enrollment.decision_note = note[:500] if note else None

    audit.log_action(
        action,
        "Enrollment",
        enrollment.id,
        summary=f"Enrollment {enrollment.id} -> {enrollment.status}",
    )
    db.session.commit()
    return enrollment


def drop_enrollment(actor, enrollment_id: int):
    """Withdraw a student from an active enrollment."""
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None or enrollment.status not in ("enrolled", "pending"):
        return None
    enrollment.status = "dropped"
    enrollment.decided_by_id = actor.id
    enrollment.decided_at = utcnow()
    audit.log_action(
        "enrollment_dropped", "Enrollment", enrollment.id,
        summary=f"Enrollment {enrollment.id} dropped",
    )
    db.session.commit()
    return enrollment
