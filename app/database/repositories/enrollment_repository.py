"""Layer 4: enrollment queries and capacity locking."""
from decimal import Decimal
from sqlalchemy import func, select
from ..extensions import db
from ..models import Course, CourseOffering, Enrollment, Grade, Prerequisite, Student

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


def enrollment_facts(student, offering):
    if student is None or offering is None or offering.course is None:
        return dict(duplicate_status=None, unmet=[], enrolled=0, capacity=0)
    duplicate = db.session.execute(select(Enrollment).where(
        Enrollment.student_id == student.id, Enrollment.offering_id == offering.id,
        Enrollment.status.in_(("pending", "enrolled", "completed")))).scalars().first()
    _, unmet = _prerequisites_met(student, offering.course)
    _, enrolled, capacity = check_capacity(offering)
    return dict(duplicate_status=duplicate.status if duplicate else None,
                unmet=unmet, enrolled=enrolled, capacity=capacity)
