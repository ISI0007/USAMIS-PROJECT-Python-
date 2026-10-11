"""Integration tests: the enrollment algorithm against real PostgreSQL rows,
including the concurrency/capacity guarantee."""
import pytest

from app.models import (
    Course, CourseOffering, Department, Enrollment, Semester, Student,
)
from app.services import enrollment_service


def _setup(db, capacity=1, num_students=2):
    dept = Department(code="CS", name="CS")
    db.session.add(dept)
    db.session.flush()
    course = Course(code="CS101", title="Intro", credits=3, department_id=dept.id)
    semester = Semester(academic_year="2025/2026", term="fall", registration_open=True)
    db.session.add_all([course, semester])
    db.session.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id,
                              capacity=capacity, is_active=True)
    db.session.add(offering)
    students = []
    for i in range(num_students):
        s = Student(student_number=f"S-{i:04d}", first_name=f"S{i}", last_name="T",
                    enrollment_status="active")
        db.session.add(s)
        students.append(s)
    db.session.commit()
    return students, offering


def test_eligible_student_can_enroll(db):
    students, offering = _setup(db, capacity=5)
    enrollment, result = enrollment_service.request_enrollment(students[0], offering)
    assert result.eligible is True
    assert enrollment is not None
    assert enrollment.status == "pending"


def test_capacity_full_rejects(db):
    students, offering = _setup(db, capacity=1, num_students=2)
    first, r1 = enrollment_service.request_enrollment(students[0], offering, auto_approve=True)
    assert r1.eligible
    second, r2 = enrollment_service.request_enrollment(students[1], offering)
    assert r2.eligible is False
    assert r2.reason_code == "CAPACITY_FULL"
    assert second is None


def test_duplicate_enrollment_rejected(db):
    students, offering = _setup(db, capacity=5, num_students=1)
    first, r1 = enrollment_service.request_enrollment(students[0], offering)
    assert r1.eligible
    second, r2 = enrollment_service.request_enrollment(students[0], offering)
    assert r2.eligible is False
    assert r2.reason_code == "ALREADY_ENROLLED"


def test_inactive_student_rejected(db):
    students, offering = _setup(db, capacity=5, num_students=1)
    students[0].enrollment_status = "withdrawn"
    db.session.commit()
    _, result = enrollment_service.request_enrollment(students[0], offering)
    assert result.eligible is False
    assert result.reason_code == "STUDENT_NOT_ACTIVE"


def test_closed_registration_rejected(db):
    students, offering = _setup(db, capacity=5, num_students=1)
    offering.semester.registration_open = False
    db.session.commit()
    _, result = enrollment_service.request_enrollment(students[0], offering)
    assert result.eligible is False
    assert result.reason_code == "REGISTRATION_CLOSED"


def test_prerequisite_not_met_rejected(db):
    from app.models import Prerequisite

    students, offering = _setup(db, capacity=5, num_students=1)
    prereq_course = Course(code="CS100", title="Pre", credits=3)
    db.session.add(prereq_course)
    db.session.flush()
    db.session.add(Prerequisite(course_id=offering.course_id,
                                required_course_id=prereq_course.id))
    db.session.commit()
    _, result = enrollment_service.request_enrollment(students[0], offering)
    assert result.eligible is False
    assert result.reason_code == "PREREQUISITE_NOT_MET"


def test_approval_flow(db, make_user):
    students, offering = _setup(db, capacity=5, num_students=1)
    admin = make_user(username="adm", role="administrator")
    enrollment, _ = enrollment_service.request_enrollment(students[0], offering)
    updated = enrollment_service.decide(admin, enrollment.id, approve=True)
    assert updated.status == "enrolled"


def test_rejection_flow(db, make_user):
    students, offering = _setup(db, capacity=5, num_students=1)
    admin = make_user(username="adm2", role="administrator")
    enrollment, _ = enrollment_service.request_enrollment(students[0], offering)
    updated = enrollment_service.decide(admin, enrollment.id, approve=False, note="Too late")
    assert updated.status == "rejected"
