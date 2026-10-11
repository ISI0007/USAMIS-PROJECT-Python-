"""Integration tests: database persistence of core entities."""
import datetime as dt

from app.models import (
    AcademicProgram, Course, CourseOffering, Department, Enrollment, Grade,
    Semester, Student,
)


def _seed_structure(db):
    dept = Department(code="CS", name="Computer Science")
    db.session.add(dept)
    db.session.flush()
    program = AcademicProgram(code="BSCS", name="BSc CS", department_id=dept.id)
    db.session.add(program)
    db.session.flush()
    student = Student(
        student_number="S-0001", first_name="Ada", last_name="Lovelace",
        department_id=dept.id, program_id=program.id, enrollment_status="active",
    )
    course = Course(code="CS101", title="Intro", credits=3, department_id=dept.id)
    semester = Semester(academic_year="2025/2026", term="fall", registration_open=True)
    db.session.add_all([student, course, semester])
    db.session.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id, capacity=30)
    db.session.add(offering)
    db.session.commit()
    return student, offering


def test_student_persists(db):
    student, _ = _seed_structure(db)
    fetched = db.session.get(Student, student.id)
    assert fetched.student_number == "S-0001"
    assert fetched.full_name == "Ada Lovelace"


def test_unique_student_number_enforced(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    _seed_structure(db)
    duplicate = Student(student_number="S-0001", first_name="X", last_name="Y")
    db.session.add(duplicate)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_enrollment_relationship(db):
    student, offering = _seed_structure(db)
    enrollment = Enrollment(student_id=student.id, offering_id=offering.id,
                            status="enrolled")
    db.session.add(enrollment)
    db.session.commit()
    assert offering.enrolled_count == 1
    assert offering.available_seats == 29


def test_duplicate_active_enrollment_rejected(db):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models import Enrollment as Enr

    student, offering = _seed_structure(db)
    db.session.add(Enr(student_id=student.id, offering_id=offering.id, status="enrolled"))
    db.session.commit()
    db.session.add(Enr(student_id=student.id, offering_id=offering.id, status="enrolled"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_grade_range_constraint(db):
    import pytest
    from decimal import Decimal
    from sqlalchemy.exc import IntegrityError

    student, offering = _seed_structure(db)
    enrollment = Enrollment(student_id=student.id, offering_id=offering.id,
                            status="enrolled")
    db.session.add(enrollment)
    db.session.commit()
    db.session.add(Grade(enrollment_id=enrollment.id, student_id=student.id,
                         score=Decimal("150.00")))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_course_credit_check_constraint(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    db.session.add(Course(code="BAD", title="Bad", credits=0))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_audit_log_created_for_grade_change(db, app):
    from app.models import AuditLog, User
    from app.services import grade_service

    student, offering = _seed_structure(db)
    teacher_user = User(username="t1", email="t1@test.local", full_name="Teacher",
                        role="teacher")
    teacher_user.set_password("Test_Pass1!")
    db.session.add(teacher_user)
    db.session.flush()
    from app.models import Teacher

    teacher = Teacher(staff_number="T-1", first_name="T", last_name="One",
                      user_id=teacher_user.id)
    db.session.add(teacher)
    db.session.flush()
    offering.teacher_id = teacher.id
    enrollment = Enrollment(student_id=student.id, offering_id=offering.id,
                            status="enrolled")
    db.session.add(enrollment)
    db.session.commit()

    grade_service.record_grade(teacher_user, enrollment.id, 88, publish=True)
    logs = db.session.query(AuditLog).filter(AuditLog.action.in_(
        ("grade_created", "grade_published"))).count()
    assert logs >= 2
