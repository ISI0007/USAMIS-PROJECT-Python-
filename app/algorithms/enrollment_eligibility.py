"""Algorithm 1 — Course Enrollment Eligibility.

Determines whether a student satisfies every rule required to enroll in a
course offering. Pure, deterministic, and unit-testable: it never reads the
Flask request and never trusts client claims.

See ``docs/ALGORITHMS.md`` for the full specification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import Course, CourseOffering, Enrollment, Grade, Prerequisite, Student


# Machine-readable reason codes returned alongside the human explanation.
REASON_OK = "ELIGIBLE"
REASON_STUDENT_MISSING = "STUDENT_NOT_FOUND"
REASON_STUDENT_INACTIVE = "STUDENT_NOT_ACTIVE"
REASON_COURSE_MISSING = "COURSE_NOT_FOUND"
REASON_OFFERING_MISSING = "OFFERING_NOT_FOUND"
REASON_OFFERING_INACTIVE = "OFFERING_INACTIVE"
REASON_REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
REASON_ALREADY_ENROLLED = "ALREADY_ENROLLED"
REASON_PREREQUISITE_MISSING = "PREREQUISITE_NOT_MET"
REASON_CAPACITY_FULL = "CAPACITY_FULL"


@dataclass
class EligibilityResult:
    """Structured eligibility outcome."""

    eligible: bool
    reason_code: str
    message: str
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "reason_code": self.reason_code,
            "message": self.message,
            "reasons": list(self.reasons),
            "details": dict(self.details),
        }


def _prerequisites_met(student: Student, course: Course) -> tuple[bool, list[str]]:
    """Return (met, unmet_descriptions).

    A prerequisite is satisfied when the student has a *published* passing
    grade (>= min_grade or the course pass mark) for the required course.
    """
    prereqs: list[Prerequisite] = (
        db.session.execute(
            select(Prerequisite).where(Prerequisite.course_id == course.id)
        )
        .scalars()
        .all()
    )
    unmet: list[str] = []
    for prereq in prereqs:
        required = db.session.get(Course, prereq.required_course_id)
        if required is None:
            continue
        threshold = (
            Decimal(str(prereq.min_grade))
            if prereq.min_grade is not None
            else Decimal("50.00")
        )
        # Best published grade the student obtained in any offering of the
        # required course. Built as a proper subquery so SQLAlchemy can
        # compose the IN clause correctly.
        offering_ids = select(CourseOffering.id).where(
            CourseOffering.course_id == required.id
        )
        score = db.session.execute(
            select(func.max(Grade.score))
            .join(Enrollment, Grade.enrollment_id == Enrollment.id)
            .where(
                Enrollment.student_id == student.id,
                Enrollment.offering_id.in_(offering_ids),
                Grade.is_published.is_(True),
            )
        ).scalar()
        if score is None or Decimal(str(score)) < threshold:
            unmet.append(
                f"{required.code} (need >= {threshold})"
            )
    return (len(unmet) == 0), unmet


def check_capacity(offering, lock: bool = False) -> tuple[bool, int, int]:
    """Check available capacity for ``offering``.

    When ``lock`` is True the offering row is selected ``FOR UPDATE`` so two
    concurrent transactions cannot both admit the final seat. This relies on
    PostgreSQL row locking; on SQLite the clause is a no-op (documented).

    Returns ``(has_room, enrolled_count, capacity)``.
    """
    if lock:
        offering = db.session.execute(
            select(type(offering))
            .where(type(offering).id == offering.id)
            .with_for_update()
        ).scalar_one()

    enrolled = db.session.execute(
        select(func.count(Enrollment.id)).where(
            Enrollment.offering_id == offering.id,
            Enrollment.status.in_(("enrolled", "completed")),
        )
    ).scalar_one()

    return enrolled < offering.capacity, int(enrolled), int(offering.capacity)


def evaluate_enrollment(
    student: Student | None,
    offering,
    *,
    lock_capacity: bool = False,
) -> EligibilityResult:
    """Evaluate eligibility of ``student`` for ``offering``.

    The checks run in a documented order and each failure returns a
    structured result with a clear reason code. Capacity is checked with an
    optional row lock for concurrency safety.
    """
    details: dict = {}

    # 1. Student exists and is active.
    if student is None:
        return EligibilityResult(False, REASON_STUDENT_MISSING, "Student not found.")
    if student.enrollment_status != "active":
        return EligibilityResult(
            False,
            REASON_STUDENT_INACTIVE,
            f"Student status is '{student.enrollment_status}', not active.",
        )

    # 2. Offering exists, is active and its semester is open for registration.
    if offering is None:
        return EligibilityResult(False, REASON_OFFERING_MISSING, "Course offering not found.")
    if not offering.is_active:
        return EligibilityResult(
            False, REASON_OFFERING_INACTIVE, "This course offering is not active."
        )
    semester = offering.semester
    if semester is not None and not semester.registration_open:
        return EligibilityResult(
            False, REASON_REGISTRATION_CLOSED, "Registration is closed for this semester."
        )

    course = offering.course
    if course is None:
        return EligibilityResult(False, REASON_COURSE_MISSING, "Course not found.")
    if not course.is_active:
        return EligibilityResult(
            False, REASON_COURSE_MISSING, f"Course {course.code} is not active."
        )

    # 3. Duplicate active enrollment.
    duplicate = db.session.execute(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.offering_id == offering.id,
            Enrollment.status.in_(("pending", "enrolled", "completed")),
        )
    ).scalars().first()
    if duplicate is not None:
        return EligibilityResult(
            False,
            REASON_ALREADY_ENROLLED,
            f"Already {duplicate.status} in {course.code}.",
        )

    # 4. Prerequisites.
    met, unmet = _prerequisites_met(student, course)
    if not met:
        return EligibilityResult(
            False,
            REASON_PREREQUISITE_MISSING,
            "Prerequisite requirements are not satisfied.",
            reasons=unmet,
            details={"unmet_prerequisites": unmet},
        )

    # 5. Capacity (optionally with a row lock to protect against races).
    has_room, enrolled, capacity = check_capacity(offering, lock=lock_capacity)
    details.update({"enrolled": enrolled, "capacity": capacity})
    if not has_room:
        return EligibilityResult(
            False,
            REASON_CAPACITY_FULL,
            f"Course is full ({enrolled}/{capacity}).",
            details=details,
        )

    return EligibilityResult(
        True,
        REASON_OK,
        f"Eligible to enroll in {course.code}.",
        details=details,
    )
