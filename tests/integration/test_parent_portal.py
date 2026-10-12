"""Integration tests: parent portal (F5).

Proves the read-only parent area works and — critically — that a parent can
only ever reach the students linked to their own account.
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
    ParentLink,
    Semester,
    Student,
)
from app.security.permissions import ROLE_PERMISSIONS


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
    return offering


def _student(db, number, first="Child", last="One"):
    s = Student(student_number=number, first_name=first, last_name=last,
                enrollment_status="active")
    db.session.add(s)
    db.session.commit()
    return s


def _grade(db, student, offering, score=75):
    e = Enrollment(student_id=student.id, offering_id=offering.id, status="completed")
    db.session.add(e)
    db.session.commit()
    db.session.add(Grade(enrollment_id=e.id, student_id=student.id,
                         score=Decimal(score), letter="B", is_published=True))
    db.session.commit()
    return e


def _link(db, parent_user, student, relationship="guardian", active=True):
    link = ParentLink(parent_user_id=parent_user.id, student_id=student.id,
                      relationship_type=relationship, is_active=active)
    db.session.add(link)
    db.session.commit()
    return link


# --------------------------------------------------------------------------
# Permission matrix
# --------------------------------------------------------------------------
def test_parent_role_has_only_linked_student_permission():
    perms = ROLE_PERMISSIONS["parent"]
    assert perms == {"view_linked_students"}


def test_parent_cannot_manage_anything():
    for forbidden in ("manage_students", "manage_fees", "view_grades",
                      "manage_enrollments", "enter_grades"):
        assert forbidden not in ROLE_PERMISSIONS["parent"]


# --------------------------------------------------------------------------
# Portal index
# --------------------------------------------------------------------------
def test_parent_index_lists_only_linked_students(client, make_user, login, db):
    offering = _structure(db)
    parent = make_user(username="parent1", role="parent")
    mine = _student(db, "S-1001", "Mine", "Child")
    other = _student(db, "S-1002", "Other", "Child")
    _grade(db, mine, offering, 80)
    _grade(db, other, offering, 90)
    _link(db, parent, mine)

    login("parent1")
    resp = client.get("/parents/")
    assert resp.status_code == 200
    assert b"S-1001" in resp.data
    assert b"S-1002" not in resp.data


def test_parent_with_no_links_sees_empty_state(client, make_user, login, db):
    make_user(username="parent2", role="parent")
    login("parent2")
    resp = client.get("/parents/")
    assert resp.status_code == 200
    assert b"No students are linked" in resp.data


# --------------------------------------------------------------------------
# Ownership enforcement (the security-critical part)
# --------------------------------------------------------------------------
def test_parent_can_view_own_child_detail(client, make_user, login, db):
    offering = _structure(db)
    parent = make_user(username="parent3", role="parent")
    mine = _student(db, "S-2001", "Mine", "Child")
    _grade(db, mine, offering, 85)
    _link(db, parent, mine)

    login("parent3")
    resp = client.get(f"/parents/student/{mine.id}")
    assert resp.status_code == 200
    assert b"Mine Child" in resp.data


def test_parent_cannot_view_unlinked_student(client, make_user, login, db):
    offering = _structure(db)
    parent = make_user(username="parent4", role="parent")
    mine = _student(db, "S-3001", "Mine", "Child")
    stranger = _student(db, "S-3002", "Stranger", "Child")
    _link(db, parent, mine)

    login("parent4")
    # Unlinked student -> 404 (not 403), so IDs cannot be probed.
    resp = client.get(f"/parents/student/{stranger.id}")
    assert resp.status_code == 404


def test_inactive_link_blocks_access(client, make_user, login, db):
    offering = _structure(db)
    parent = make_user(username="parent5", role="parent")
    child = _student(db, "S-4001", "Old", "Child")
    _link(db, parent, child, active=False)

    login("parent5")
    assert client.get("/parents/").status_code == 200
    resp = client.get(f"/parents/student/{child.id}")
    assert resp.status_code == 404


def test_student_cannot_reach_parent_portal(client, make_user, login):
    make_user(username="stu_p", role="student")
    login("stu_p")
    assert client.get("/parents/").status_code == 403


def test_teacher_cannot_reach_parent_portal(client, make_user, login):
    make_user(username="teach_p", role="teacher")
    login("teach_p")
    assert client.get("/parents/").status_code == 403


def test_anonymous_redirected_from_parent_portal(client):
    resp = client.get("/parents/", follow_redirects=False)
    assert resp.status_code in (302, 401)


# --------------------------------------------------------------------------
# Dashboard + detail content
# --------------------------------------------------------------------------
def test_parent_dashboard_renders(client, make_user, login, db):
    parent = make_user(username="parent6", role="parent")
    child = _student(db, "S-5001", "Dash", "Child")
    _link(db, parent, child)
    login("parent6")
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert b"S-5001" in resp.data


def test_parent_detail_shows_records(client, make_user, login, db):
    offering = _structure(db)
    parent = make_user(username="parent7", role="parent")
    child = _student(db, "S-6001", "Detail", "Child")
    _grade(db, child, offering, 70)
    db.session.add(Attendance(student_id=child.id, offering_id=offering.id,
                              session_date=date(2024, 9, 2), status="present"))
    db.session.commit()
    _link(db, parent, child)

    login("parent7")
    resp = client.get(f"/parents/student/{child.id}")
    assert resp.status_code == 200
    assert b"Published Grades" in resp.data
    assert b"Enrollment History" in resp.data


def test_missing_student_detail_is_404(client, make_user, login):
    make_user(username="parent8", role="parent")
    login("parent8")
    resp = client.get("/parents/student/999999")
    assert resp.status_code == 404
