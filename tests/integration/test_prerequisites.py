"""Integration tests: prerequisite enforcement against real rows."""
from app.models import (
    Course, CourseOffering, Department, Enrollment, Grade, Prerequisite, Semester,
    Student,
)
from app.services import enrollment_service


def _base(db):
    dept = Department(code="CS", name="CS")
    db.session.add(dept)
    db.session.flush()
    advance = Course(code="CS201", title="Databases", credits=3, department_id=dept.id)
    prereq_course = Course(code="CS102", title="Data Structures", credits=4,
                           department_id=dept.id)
    semester = Semester(academic_year="2025/2026", term="fall", registration_open=True)
    db.session.add_all([advance, prereq_course, semester])
    db.session.flush()
    db.session.add(Prerequisite(course_id=advance.id, required_course_id=prereq_course.id))
    offering = CourseOffering(course_id=advance.id, semester_id=semester.id, capacity=30)
    db.session.add(offering)
    db.session.commit()
    return advance, prereq_course, semester, offering


def test_missing_prerequisite_blocks_enrollment(db):
    advance, prereq_course, semester, offering = _base(db)
    student = Student(student_number="S-1", first_name="A", last_name="B",
                      enrollment_status="active")
    db.session.add(student)
    db.session.commit()

    _, result = enrollment_service.request_enrollment(student, offering)
    assert result.eligible is False
    assert result.reason_code == "PREREQUISITE_NOT_MET"
    assert any("CS102" in r for r in result.reasons)


def test_published_passing_prerequisite_allows_enrollment(db):
    advance, prereq_course, semester, offering = _base(db)
    student = Student(student_number="S-2", first_name="C", last_name="D",
                      enrollment_status="active")
    db.session.add(student)
    db.session.flush()

    # Prior completed offering of the prerequisite with a passing published grade.
    prior_offering = CourseOffering(course_id=prereq_course.id,
                                    semester_id=semester.id, capacity=30)
    db.session.add(prior_offering)
    db.session.flush()
    prior_enrollment = Enrollment(student_id=student.id,
                                  offering_id=prior_offering.id, status="completed")
    db.session.add(prior_enrollment)
    db.session.flush()
    from decimal import Decimal

    db.session.add(Grade(enrollment_id=prior_enrollment.id, student_id=student.id,
                         score=Decimal("75.00"), letter="C", is_published=True))
    db.session.commit()

    _, result = enrollment_service.request_enrollment(student, offering)
    assert result.eligible is True, result.message


def test_unpublished_prerequisite_grade_does_not_satisfy(db):
    advance, prereq_course, semester, offering = _base(db)
    student = Student(student_number="S-3", first_name="E", last_name="F",
                      enrollment_status="active")
    db.session.add(student)
    db.session.flush()
    prior_offering = CourseOffering(course_id=prereq_course.id,
                                    semester_id=semester.id, capacity=30)
    db.session.add(prior_offering)
    db.session.flush()
    prior_enrollment = Enrollment(student_id=student.id,
                                  offering_id=prior_offering.id, status="completed")
    db.session.add(prior_enrollment)
    db.session.flush()
    from decimal import Decimal

    db.session.add(Grade(enrollment_id=prior_enrollment.id, student_id=student.id,
                         score=Decimal("90.00"), letter="A", is_published=False))
    db.session.commit()

    _, result = enrollment_service.request_enrollment(student, offering)
    assert result.eligible is False
    assert result.reason_code == "PREREQUISITE_NOT_MET"
