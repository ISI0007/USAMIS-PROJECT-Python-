"""Security tests: authentication and authorization boundaries.

These are negative tests proving that unauthorized users cannot reach
protected resources, and that ownership is enforced server-side.
"""
from app.models import (
    Course, CourseOffering, Department, Enrollment, Semester, Student, Teacher,
)


def _academic_setup(db):
    dept = Department(code="CS", name="CS")
    db.session.add(dept)
    db.session.flush()
    course = Course(code="CS101", title="Intro", credits=3, department_id=dept.id)
    semester = Semester(academic_year="2025/2026", term="fall", registration_open=True)
    db.session.add_all([course, semester])
    db.session.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id, capacity=30)
    db.session.add(offering)
    db.session.commit()
    return offering


def test_anonymous_cannot_reach_dashboard(client):
    resp = client.get("/dashboard/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("Location", "")


def test_anonymous_cannot_reach_students(client):
    resp = client.get("/students/", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_anonymous_cannot_list_users(client):
    resp = client.get("/admin/users", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_student_cannot_view_management_pages(client, make_user, login, app):
    with app.app_context():
        make_user(username="stu1", role="student")
    login("stu1")
    for path in ("/students/", "/departments/", "/programs/", "/courses/",
                 "/semesters/", "/enrollments/", "/fees/", "/reports/", "/admin/users"):
        resp = client.get(path)
        assert resp.status_code == 403, f"student reached {path}"


def test_student_cannot_view_another_students_profile(client, make_user, login, app):
    with app.app_context():
        make_user(username="stuA", role="student")
        other = Student(student_number="S-9001", first_name="Other", last_name="Person",
                        enrollment_status="active")
        app.extensions["sqlalchemy"].session.add(other)
        app.extensions["sqlalchemy"].session.commit()
        other_id = other.id

    login("stuA")
    resp = client.get(f"/students/{other_id}")
    assert resp.status_code == 403


def test_teacher_cannot_reach_admin_users(client, make_user, login, app):
    with app.app_context():
        make_user(username="tea1", role="teacher")
    login("tea1")
    assert client.get("/admin/users").status_code == 403


def test_finance_cannot_manage_courses(client, make_user, login, app):
    with app.app_context():
        make_user(username="fin1", role="finance")
    login("fin1")
    # Fees are allowed, course administration is not.
    assert client.get("/fees/").status_code == 200
    assert client.get("/courses/new").status_code == 403


def test_academic_staff_cannot_view_audit_log(client, make_user, login, app):
    with app.app_context():
        make_user(username="staff1", role="academic_staff")
    login("staff1")
    assert client.get("/admin/audit").status_code == 403


def test_teacher_cannot_grade_unassigned_course(client, make_user, login, app):
    from app.extensions import db as _db

    with app.app_context():
        make_user(username="tea2", role="teacher")
        offering = _academic_setup(_db)
        offering_id = offering.id
    login("tea2")
    resp = client.get(f"/grades/offering/{offering_id}")
    assert resp.status_code == 403


def test_student_cannot_post_grade(client, make_user, login, app):
    with app.app_context():
        make_user(username="stu2", role="student")
    login("stu2")
    # Any attempt to hit grade entry endpoints is forbidden.
    resp = client.post("/grades/enrollment/1", data={"score": "100", "publish": "on"})
    assert resp.status_code in (403, 404)


def test_unauthenticated_cannot_create_student(client):
    resp = client.post("/students/new", data={"student_number": "S-X"})
    assert resp.status_code in (302, 401)


def test_admin_can_access_admin_pages(client, make_user, login, app):
    with app.app_context():
        make_user(username="adm9", role="administrator")
    login("adm9")
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/audit").status_code == 200
    assert client.get("/admin/roles").status_code == 200


def test_security_headers_present(client):
    resp = client.get("/auth/login")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_admin_cannot_deactivate_self(client, make_user, login, app):
    with app.app_context():
        user = make_user(username="adm10", role="administrator")
        uid = user.id
    login("adm10")
    resp = client.post(f"/admin/users/{uid}/toggle", follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot deactivate your own account" in resp.data
