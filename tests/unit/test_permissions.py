"""Unit tests for RBAC permission logic (pure functions)."""
from app.security.permissions import (
    Permission,
    Role,
    permissions_for,
    role_has_permission,
)


def test_admin_has_all_critical_permissions():
    for perm in (Permission.MANAGE_USERS, Permission.VIEW_AUDIT_LOG,
                 Permission.MANAGE_FEES, Permission.ENTER_GRADES):
        assert role_has_permission(Role.ADMIN, perm)


def test_student_cannot_manage_students():
    assert not role_has_permission(Role.STUDENT, Permission.MANAGE_STUDENTS)


def test_student_cannot_enter_grades():
    assert not role_has_permission(Role.STUDENT, Permission.ENTER_GRADES)


def test_student_cannot_manage_fees():
    assert not role_has_permission(Role.STUDENT, Permission.MANAGE_FEES)


def test_student_can_view_own_records():
    for perm in (Permission.VIEW_OWN_GRADES, Permission.VIEW_OWN_FEES,
                 Permission.VIEW_OWN_ATTENDANCE, Permission.VIEW_OWN_ENROLLMENT):
        assert role_has_permission(Role.STUDENT, perm)


def test_teacher_can_enter_grades_but_not_manage_fees():
    assert role_has_permission(Role.TEACHER, Permission.ENTER_GRADES)
    assert not role_has_permission(Role.TEACHER, Permission.MANAGE_FEES)


def test_finance_can_manage_fees_only():
    assert role_has_permission(Role.FINANCE, Permission.MANAGE_FEES)
    assert not role_has_permission(Role.FINANCE, Permission.MANAGE_USERS)
    assert not role_has_permission(Role.FINANCE, Permission.ENTER_GRADES)


def test_academic_staff_cannot_view_audit_log():
    assert not role_has_permission(Role.ACADEMIC_STAFF, Permission.VIEW_AUDIT_LOG)


def test_unknown_role_has_no_permissions():
    assert permissions_for("does-not-exist") == set()
    assert not role_has_permission("does-not-exist", Permission.MANAGE_USERS)
