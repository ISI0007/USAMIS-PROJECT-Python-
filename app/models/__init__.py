"""SQLAlchemy models for USAMIS-Python.

The models are grouped in this package and re-exported here so that
``from app.models import X`` works regardless of the internal module split.
"""
from .mixins import utcnow  # noqa: F401
from .user import User, AuditLog  # noqa: F401
from .academic import (  # noqa: F401
    Department,
    AcademicProgram,
    Student,
    Teacher,
    Course,
    Prerequisite,
    Semester,
    CourseOffering,
)
from .enrollment import Enrollment  # noqa: F401
from .grade import Grade  # noqa: F401
from .attendance import Attendance  # noqa: F401
from .fee import FeeCategory, FeeAssessment, Payment  # noqa: F401

__all__ = [
    "utcnow",
    "User",
    "AuditLog",
    "Department",
    "AcademicProgram",
    "Student",
    "Teacher",
    "Course",
    "Prerequisite",
    "Semester",
    "CourseOffering",
    "Enrollment",
    "Grade",
    "Attendance",
    "FeeCategory",
    "FeeAssessment",
    "Payment",
]
