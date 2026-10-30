"""Algorithm 1 — Course Enrollment Eligibility.

Determines whether a student satisfies every rule required to enroll in a
course offering. Pure, deterministic, and unit-testable: it never reads the
Flask request and never trusts client claims.

See ``docs/ALGORITHMS.md`` for the full specification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal



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


def evaluate_enrollment(
    student,
    offering,
    *,
    facts: dict,
) -> EligibilityResult:
    """Evaluate eligibility of ``student`` for ``offering``.

    The checks run in a documented order and each failure returns a
    structured result with a clear reason code. Capacity is checked with an
    facts snapshot retrieved by the service under an optional capacity lock.
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
    if facts['duplicate_status'] is not None:
        return EligibilityResult(False, REASON_ALREADY_ENROLLED,
                                 f"Already {facts['duplicate_status']} in {course.code}.")

    # 4. Prerequisites.
    unmet = facts['unmet']
    if unmet:
        return EligibilityResult(
            False,
            REASON_PREREQUISITE_MISSING,
            "Prerequisite requirements are not satisfied.",
            reasons=unmet,
            details={"unmet_prerequisites": unmet},
        )

    # 5. Capacity (optionally with a row lock to protect against races).
    enrolled, capacity = facts['enrolled'], facts['capacity']
    has_room = enrolled < capacity
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
