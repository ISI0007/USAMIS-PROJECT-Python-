"""Role and permission definitions for USAMIS-Python.

Authorization is enforced **server-side** for every protected operation.
Templates may hide menu items as a convenience, but they are never the
security boundary.

Roles (from the requirements):
    * administrator  — full system control
    * academic_staff — registrar duties: students, courses, enrollment
    * teacher        — grades/attendance for assigned courses only
    * finance        — fees and payments
    * student        — read-only access to their own records
"""
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "administrator"
    ACADEMIC_STAFF = "academic_staff"
    TEACHER = "teacher"
    FINANCE = "finance"
    STUDENT = "student"


ROLE_LABELS: dict[str, str] = {
    Role.ADMIN: "Administrator",
    Role.ACADEMIC_STAFF: "Academic Staff",
    Role.TEACHER: "Teacher",
    Role.FINANCE: "Finance Officer",
    Role.STUDENT: "Student",
}


class Permission(StrEnum):
    # Administration
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_SETTINGS = "manage_settings"

    # Academic structure
    MANAGE_DEPARTMENTS = "manage_departments"
    MANAGE_PROGRAMS = "manage_programs"
    MANAGE_COURSES = "manage_courses"
    MANAGE_SEMESTERS = "manage_semesters"

    # Students
    MANAGE_STUDENTS = "manage_students"
    VIEW_STUDENTS = "view_students"

    # Enrollment
    MANAGE_ENROLLMENTS = "manage_enrollments"
    REQUEST_ENROLLMENT = "request_enrollment"
    VIEW_OWN_ENROLLMENT = "view_own_enrollment"

    # Grades
    ENTER_GRADES = "enter_grades"
    PUBLISH_GRADES = "publish_grades"
    VIEW_OWN_GRADES = "view_own_grades"
    VIEW_GRADES = "view_grades"

    # Attendance
    RECORD_ATTENDANCE = "record_attendance"
    VIEW_OWN_ATTENDANCE = "view_own_attendance"

    # Fees
    MANAGE_FEES = "manage_fees"
    VIEW_OWN_FEES = "view_own_fees"

    # Notifications
    SEND_NOTIFICATIONS = "send_notifications"

    # Reports
    VIEW_REPORTS = "view_reports"


#: Permission matrix. This dict is the single source of truth used both for
#: the ``has_permission`` helper and for the ``role_permissions`` view.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOG,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_DEPARTMENTS,
        Permission.MANAGE_PROGRAMS,
        Permission.MANAGE_COURSES,
        Permission.MANAGE_SEMESTERS,
        Permission.MANAGE_STUDENTS,
        Permission.VIEW_STUDENTS,
        Permission.MANAGE_ENROLLMENTS,
        Permission.REQUEST_ENROLLMENT,
        Permission.VIEW_OWN_ENROLLMENT,
        Permission.ENTER_GRADES,
        Permission.PUBLISH_GRADES,
        Permission.VIEW_GRADES,
        Permission.VIEW_OWN_GRADES,
        Permission.RECORD_ATTENDANCE,
        Permission.VIEW_OWN_ATTENDANCE,
        Permission.MANAGE_FEES,
        Permission.SEND_NOTIFICATIONS,
        Permission.VIEW_OWN_FEES,
        Permission.VIEW_REPORTS,
    },
    Role.ACADEMIC_STAFF: {
        Permission.MANAGE_DEPARTMENTS,
        Permission.MANAGE_PROGRAMS,
        Permission.MANAGE_COURSES,
        Permission.MANAGE_SEMESTERS,
        Permission.MANAGE_STUDENTS,
        Permission.VIEW_STUDENTS,
        Permission.MANAGE_ENROLLMENTS,
        Permission.VIEW_GRADES,
        Permission.VIEW_REPORTS,
    },
    Role.TEACHER: {
        Permission.ENTER_GRADES,
        Permission.PUBLISH_GRADES,
        Permission.RECORD_ATTENDANCE,
        Permission.VIEW_STUDENTS,
        Permission.VIEW_GRADES,
        Permission.VIEW_REPORTS,
    },
    Role.FINANCE: {
        Permission.MANAGE_FEES,
        Permission.SEND_NOTIFICATIONS,
        Permission.VIEW_STUDENTS,
        Permission.VIEW_REPORTS,
    },
    Role.STUDENT: {
        Permission.VIEW_OWN_ENROLLMENT,
        Permission.REQUEST_ENROLLMENT,
        Permission.VIEW_OWN_GRADES,
        Permission.VIEW_OWN_ATTENDANCE,
        Permission.VIEW_OWN_FEES,
    },
}


def permissions_for(role: str) -> set[str]:
    """Return the permission set for a role name."""
    return set(ROLE_PERMISSIONS.get(role, set()))


def role_has_permission(role: str, permission: str) -> bool:
    """Pure check used by ``User.has_permission`` and by tests."""
    return permission in ROLE_PERMISSIONS.get(role, set())
