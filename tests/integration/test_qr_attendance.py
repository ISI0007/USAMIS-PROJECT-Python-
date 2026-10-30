"""Integration tests: QR-code attendance (F3).

Covers signed-token generation and verification, session lifecycle, enrollment
checks, idempotent scanning, expiry/closure, and the HTTP routes + RBAC.
"""
import datetime as dt

import pytest

from app.extensions import db as _db
from app.models import (
    Attendance, AttendanceSession, Course, CourseOffering, Department,
    Enrollment, Semester, Student, Teacher, User,
)
from app.services import qr_attendance_service
from app.services.qr_attendance_service import QRAttendanceError

SECRET = "test-secret-key"


# --------------------------------------------------------------------------
# Fixtures: a minimal academic graph
# --------------------------------------------------------------------------
def _graph(db, *, with_student_user: bool = True):
    """Create dept -> course -> offering -> enrolled student. Returns a dict."""
    dept = Department(code="CSE", name="Computer Science")
    db.session.add(dept)
    db.session.commit()

    teacher_user = User(username="qrteacher", email="t@test.local",
                        full_name="Q Teacher", role="teacher", status="active",
                        is_active_flag=True)
    teacher_user.set_password("Test_Pass1!")
    db.session.add(teacher_user)
    db.session.commit()

    teacher = Teacher(user_id=teacher_user.id, first_name="Q", last_name="Teacher",
                      staff_number="T-001")
    db.session.add(teacher)
    db.session.commit()

    course = Course(code="CSE101", title="Intro", credits=3, department_id=dept.id)
    db.session.add(course)
    db.session.commit()

    semester = Semester(academic_year="2026/2027", term="fall", is_active=True,
                        registration_open=True)
    db.session.add(semester)
    db.session.commit()

    offering = CourseOffering(course_id=course.id, teacher_id=teacher.id,
                              semester_id=semester.id)
    db.session.add(offering)
    db.session.commit()

    student = Student(student_number="S-QR1", first_name="Q", last_name="Student",
                      enrollment_status="active", department_id=dept.id)
    db.session.add(student)
    db.session.commit()

    if with_student_user:
        su = User(username="qrstudent", email="s@test.local", full_name="Q Student",
                  role="student", status="active", is_active_flag=True)
        su.set_password("Test_Pass1!")
        db.session.add(su)
        db.session.commit()
        student.user_id = su.id
        db.session.commit()

    db.session.add(Enrollment(student_id=student.id, offering_id=offering.id,
                              status="enrolled"))
    db.session.commit()

    return {"teacher_user": teacher_user, "teacher": teacher, "course": course,
            "offering": offering, "student": student, "dept": dept}


# --------------------------------------------------------------------------
# Token signing
# --------------------------------------------------------------------------
def test_token_roundtrip_and_tamper_rejection():
    expires = dt.datetime.utcnow() + dt.timedelta(minutes=15)
    token = qr_attendance_service.generate_token(5, 9, expires, SECRET)
    verified = qr_attendance_service.verify_token(token, SECRET)
    assert verified is not None
    sid, oid, exp = verified
    assert sid == 5 and oid == 9 and exp == int(expires.timestamp())

    # tampered signature
    assert qr_attendance_service.verify_token(token[:-4] + "0000", SECRET) is None
    # wrong secret
    assert qr_attendance_service.verify_token(token, "other-secret") is None
    # malformed
    assert qr_attendance_service.verify_token("nonsense", SECRET) is None
    assert qr_attendance_service.verify_token("1:2:3", SECRET) is None


# --------------------------------------------------------------------------
# Session lifecycle
# --------------------------------------------------------------------------
def test_open_session_closes_previous(db):
    g = _graph(db)
    s1 = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                            ttl_minutes=10, secret=SECRET)
    s2 = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                            ttl_minutes=10, secret=SECRET)
    _db.session.refresh(s1)
    assert s1.is_open is False
    assert s2.is_open is True
    assert s2.is_active() is True


def test_open_session_rejects_bad_ttl(db):
    g = _graph(db)
    with pytest.raises(QRAttendanceError):
        qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                           ttl_minutes=0, secret=SECRET)
    with pytest.raises(QRAttendanceError):
        qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                           ttl_minutes=999, secret=SECRET)


def test_scan_marks_present_and_is_idempotent(db):
    g = _graph(db)
    session = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                                 ttl_minutes=10, secret=SECRET)
    su = _db.session.get(User, g["student"].user_id)

    record = qr_attendance_service.scan(su, session.token, secret=SECRET)
    assert record.status == "present"
    assert record.source == "qr"
    assert record.session_id == session.id

    # rescan updates, does not duplicate
    qr_attendance_service.scan(su, session.token, secret=SECRET)
    n = _db.session.scalar(_db.select(_db.func.count(Attendance.id)))
    assert n == 1


def test_scan_rejects_invalid_token(db):
    g = _graph(db)
    su = _db.session.get(User, g["student"].user_id)
    with pytest.raises(QRAttendanceError):
        qr_attendance_service.scan(su, "bogus", secret=SECRET)


def test_scan_rejects_closed_session(db):
    g = _graph(db)
    session = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                                 ttl_minutes=10, secret=SECRET)
    qr_attendance_service.close_session(g["teacher_user"], session)
    su = _db.session.get(User, g["student"].user_id)
    with pytest.raises(QRAttendanceError):
        qr_attendance_service.scan(su, session.token, secret=SECRET)


def test_scan_rejects_unenrolled_student(db):
    g = _graph(db)
    session = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                                 ttl_minutes=10, secret=SECRET)
    # a second student, not enrolled
    other = User(username="outsider", email="o@test.local", full_name="Out Sider",
                 role="student", status="active", is_active_flag=True)
    other.set_password("Test_Pass1!")
    _db.session.add(other)
    _db.session.commit()
    s2 = Student(student_number="S-QR2", first_name="Out", last_name="Sider",
                 enrollment_status="active", user_id=other.id)
    _db.session.add(s2)
    _db.session.commit()

    with pytest.raises(QRAttendanceError):
        qr_attendance_service.scan(other, session.token, secret=SECRET)


def test_scan_rejects_expired_token(db):
    g = _graph(db)
    # open, then force-expire the session
    session = qr_attendance_service.open_session(g["teacher_user"], g["offering"],
                                                 ttl_minutes=10, secret=SECRET)
    session.expires_at = dt.datetime.utcnow() - dt.timedelta(minutes=1)
    _db.session.commit()
    su = _db.session.get(User, g["student"].user_id)
    with pytest.raises(QRAttendanceError):
        qr_attendance_service.scan(su, session.token, secret=SECRET)


# --------------------------------------------------------------------------
# HTTP routes + RBAC
# --------------------------------------------------------------------------
def test_qr_session_page_requires_login(client):
    assert client.get("/attendance/offering/1/session").status_code in (302, 401)


def test_student_denied_qr_session_page(client, login, make_user):
    make_user(username="qr_stu2", role="student")
    login("qr_stu2")
    assert client.get("/attendance/offering/1/session").status_code == 403


def test_qr_image_returns_png(client, login, make_user, app, db):
    with app.app_context():
        g = _graph(db)
        session = qr_attendance_service.open_session(
            g["teacher_user"], g["offering"], ttl_minutes=10,
            secret=app.config["SECRET_KEY"])
        token = session.token
        from app.models import User as U
        tu = _db.session.get(U, g["teacher_user"].id)
        tu.set_password("Teacher_Pass1!")
        _db.session.commit()

    login("qrteacher", password="Teacher_Pass1!")
    resp = client.get(f"/attendance/qr/{token}.png")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/png"
    assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_student_scan_route_marks_present(client, login, make_user, app, db):
    with app.app_context():
        g = _graph(db)
        session = qr_attendance_service.open_session(
            g["teacher_user"], g["offering"], ttl_minutes=10,
            secret=app.config["SECRET_KEY"])
        token = session.token
        st = _db.session.get(User, g["student"].user_id)
        st.set_password("Student_Pass1!")
        _db.session.commit()

    login("qrstudent", password="Student_Pass1!")
    resp = client.get(f"/attendance/scan?token={token}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Confirm attendance" in resp.data
    with app.app_context():
        assert _db.session.scalar(_db.select(_db.func.count(Attendance.id))) == 0
    resp = client.post('/attendance/scan', data={'token': token}, follow_redirects=True)
    assert b"Attendance recorded" in resp.data
    with app.app_context():
        assert _db.session.scalar(_db.select(_db.func.count(Attendance.id))) == 1
