"""Grade business rules: entry, publication, and change auditing."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from ..algorithms.academic_performance import letter_for
from ..extensions import db
from ..models import CourseOffering, Enrollment, Grade, Teacher
from ..models.mixins import utcnow
from . import audit


class GradeError(ValueError):
    """Raised for invalid grade input or unauthorized grade operations."""


def teacher_teaches(actor, offering: CourseOffering) -> bool:
    """True when ``actor`` is the teacher assigned to ``offering``."""
    if actor.has_permission("manage_enrollments"):  # academic staff/admin override
        return True
    teacher = db.session.execute(
        db.select(Teacher).where(Teacher.user_id == actor.id)
    ).scalars().first()
    return bool(teacher and offering.teacher_id == teacher.id)


def _parse_score(score) -> Decimal:
    try:
        value = Decimal(str(score))
    except (InvalidOperation, TypeError, ValueError):
        raise GradeError("Grade must be a number.")
    if value < 0 or value > 100:
        raise GradeError("Grade must be between 0 and 100.")
    return value.quantize(Decimal("0.01"))


def record_grade(actor, enrollment_id: int, score, *, publish: bool = False, remarks: str = ""):
    """Create or update the grade for an enrollment.

    - Only the assigned teacher (or academic staff/admin) may enter grades.
    - Every change is written to the audit log.
    """
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise GradeError("Enrollment not found.")

    offering = db.session.get(CourseOffering, enrollment.offering_id)
    if not teacher_teaches(actor, offering):
        raise GradeError("You are not authorized to grade this course.")

    value = _parse_score(score)
    letter = letter_for(value)

    grade = db.session.execute(
        db.select(Grade).where(Grade.enrollment_id == enrollment_id)
    ).scalars().first()

    if grade is None:
        grade = Grade(
            enrollment_id=enrollment_id,
            student_id=enrollment.student_id,
            score=value,
            letter=letter,
            remarks=remarks[:500] if remarks else None,
            entered_by_id=actor.id,
        )
        db.session.add(grade)
        db.session.flush()
        audit.log_action(
            "grade_created", "Grade", grade.id,
            summary=f"Grade {value} ({letter}) for enrollment {enrollment_id}",
        )
    else:
        old = grade.score
        grade.score = value
        grade.letter = letter
        grade.remarks = remarks[:500] if remarks else grade.remarks
        grade.entered_by_id = actor.id
        audit.log_action(
            "grade_updated", "Grade", grade.id,
            summary=f"Grade changed {old} -> {value} ({letter}) for enrollment {enrollment_id}",
        )

    if publish:
        grade.is_published = True
        grade.published_at = utcnow()
        audit.log_action(
            "grade_published", "Grade", grade.id,
            summary=f"Grade published for enrollment {enrollment_id}",
        )

    if enrollment.status == "enrolled" and publish:
        enrollment.status = "completed"

    db.session.commit()
    return grade


def publish_grade(actor, grade_id: int):
    """Publish a previously entered grade."""
    grade = db.session.get(Grade, grade_id)
    if grade is None:
        return None
    offering = db.session.get(CourseOffering, grade.enrollment.offering_id)
    if not teacher_teaches(actor, offering):
        raise GradeError("You are not authorized to publish this grade.")
    grade.is_published = True
    grade.published_at = utcnow()
    audit.log_action("grade_published", "Grade", grade.id, summary="Grade published")
    db.session.commit()
    return grade
