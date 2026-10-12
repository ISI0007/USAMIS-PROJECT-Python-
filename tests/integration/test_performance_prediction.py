"""Integration tests: AI performance prediction (F4).

Covers the prediction service against real stored grades/attendance, the
cohort board, and the HTTP routes including RBAC.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db as _db
from app.models import (
    Attendance,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Grade,
    Semester,
    Student,
)
from app.services import prediction_service


@pytest.fixture(autouse=True)
def _students_role(make_user):
    """Ensure a staff user exists for the client tests."""
    return None


def _structure(db):
    dept = Department(code="0809", name="Software Engineering")
    db.session.add(dept)
    db.session.commit()
    course = Course(code="CS101", title="Intro to CS", credits=3, department_id=dept.id)
    sem = Semester(academic_year="2024/25", term="fall", is_active=True)
    db.session.add_all([course, sem])
    db.session.commit()
    offering = CourseOffering(course_id=course.id, semester_id=sem.id, capacity=40)
    db.session.add(offering)
    db.session.commit()
    return dept, course, sem, offering


def _student(db, number="S-2001"):
    s = Student(student_number=number, first_name="Test", last_name="Student",
                enrollment_status="active")
    db.session.add(s)
    db.session.commit()
    return s


def _enroll_with_grade(db, student, offering, score, published=True):
    e = Enrollment(student_id=student.id, offering_id=offering.id, status="completed")
    db.session.add(e)
    db.session.commit()
    g = Grade(enrollment_id=e.id, student_id=student.id, score=Decimal(score),
              is_published=published)
    db.session.add(g)
    db.session.commit()
    return e, g


def _attend(db, student, offering, statuses, start_day=1):
    for i, status in enumerate(statuses):
        db.session.add(Attendance(
            student_id=student.id, offering_id=offering.id,
            session_date=date(2024, 9, start_day + i), status=status,
        ))
    db.session.commit()


# --------------------------------------------------------------------------
# Service layer
# --------------------------------------------------------------------------
def test_signals_from_stored_records(db):
    _, _, _, offering = _structure(db)
    student = _student(db)
    _enroll_with_grade(db, student, offering, 80)
    _attend(db, student, offering, ["present", "present", "absent", "late"])

    signals = prediction_service.student_signals(student)
    assert signals["weighted_average"] == Decimal("80.00")
    assert signals["attendance_total"] == 4
    assert signals["attendance_present"] == 3
    assert signals["attendance_rate"] == pytest.approx(0.75)


def test_unpublished_grades_ignored_by_signals(db):
    _, _, _, offering = _structure(db)
    student = _student(db)
    _enroll_with_grade(db, student, offering, 95, published=False)
    signals = prediction_service.student_signals(student)
    assert signals["weighted_average"] is None


def test_predict_for_student_returns_result_and_signals(db):
    _, _, _, offering = _structure(db)
    student = _student(db)
    _enroll_with_grade(db, student, offering, 40)
    _attend(db, student, offering, ["absent", "absent", "present", "absent"])

    prediction, signals = prediction_service.predict_for_student(student)
    assert prediction.band == "high"
    assert prediction.has_data is True
    assert signals["attendance_rate"] == pytest.approx(0.25)
    # Factors are explained, largest absolute impact first.
    assert prediction.factors[0].name == "Academic average"


def test_predict_cohort_sorted_high_risk_first(db):
    _, _, _, offering = _structure(db)
    weak = _student(db, "S-3001")
    strong = _student(db, "S-3002")
    _enroll_with_grade(db, weak, offering, 35)
    _attend(db, weak, offering, ["absent"] * 4)
    _enroll_with_grade(db, strong, offering, 95)
    _attend(db, strong, offering, ["present"] * 4)

    rows = prediction_service.predict_cohort([weak, strong])
    # Weak student first (highest risk), strong student last.
    assert rows[0]["student"].id == weak.id
    assert rows[0]["prediction"].band == "high"
    assert rows[1]["student"].id == strong.id
    assert rows[1]["prediction"].band == "low"
    assert rows[0]["prediction"].risk_score >= rows[1]["prediction"].risk_score
    assert all(r["band_label"] and r["action"] for r in rows)


def test_student_with_no_records_has_no_data(db):
    student = _student(db)
    prediction, signals = prediction_service.predict_for_student(student)
    assert prediction.has_data is False
    assert signals["weighted_average"] is None
    assert signals["attendance_rate"] is None


# --------------------------------------------------------------------------
# HTTP routes
# --------------------------------------------------------------------------
def test_risk_board_requires_permission(client, make_user, login):
    make_user(username="stu", role="student")
    login("stu")
    resp = client.get("/predictions/")
    assert resp.status_code == 403


def test_risk_board_renders_for_staff(client, make_user, login, db):
    _, _, _, offering = _structure(db)
    _student(db, "S-4001")
    make_user(username="reg", role="academic_staff")
    login("reg")
    resp = client.get("/predictions/")
    assert resp.status_code == 200
    assert b"Academic Risk Board" in resp.data


def test_risk_board_band_filter(client, make_user, login, db):
    _, _, _, offering = _structure(db)
    weak = _student(db, "S-5001")
    _enroll_with_grade(db, weak, offering, 30)
    _attend(db, weak, offering, ["absent"] * 4)
    make_user(username="reg2", role="academic_staff")
    login("reg2")
    resp = client.get("/predictions/?band=high")
    assert resp.status_code == 200
    # This struggling student scores *high* risk under the corrected model, so
    # they must appear in the high filter and be excluded from the low filter.
    assert b"S-5001" in resp.data
    resp_low = client.get("/predictions/?band=low")
    assert b"S-5001" not in resp_low.data


def test_student_detail_explains_factors(client, make_user, login, db):
    _, _, _, offering = _structure(db)
    student = _student(db, "S-6001")
    _enroll_with_grade(db, student, offering, 45)
    _attend(db, student, offering, ["absent", "present"])
    make_user(username="reg3", role="academic_staff")
    login("reg3")
    resp = client.get(f"/predictions/student/{student.id}")
    assert resp.status_code == 200
    assert b"Academic average" in resp.data
    assert b"Attendance" in resp.data


def test_student_detail_missing_returns_404(client, make_user, login):
    make_user(username="reg4", role="academic_staff")
    login("reg4")
    resp = client.get("/predictions/student/999999")
    assert resp.status_code == 404


def test_teacher_can_view_risk_board(client, make_user, login, db):
    make_user(username="teach", role="teacher")
    login("teach")
    resp = client.get("/predictions/")
    assert resp.status_code == 200


def test_student_dashboard_shows_risk_panel(client, make_user, login, db):
    _, _, _, offering = _structure(db)
    user = make_user(username="selfstu", role="student")
    student = Student(student_number="S-7001", first_name="Self", last_name="Stu",
                      enrollment_status="active", user_id=user.id)
    db.session.add(student)
    db.session.commit()
    _enroll_with_grade(db, student, offering, 55)
    _attend(db, student, offering, ["absent", "absent", "present", "absent"])
    login("selfstu")
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert b"Academic Risk Insight" in resp.data
