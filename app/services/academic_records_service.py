"""Academic records service.

Builds the row data for the student "Academic Records" page from authenticated
student data: every course the student has (any enrollment status) joined with
its semester, offering, course, department and grade.

Design notes
------------
* No new database tables are introduced — the feature reuses the existing
  ``Enrollment``, ``CourseOffering``, ``Course``, ``Semester``, ``Department``
  and ``Grade`` models.
* Fields the institution does not store (makeup-exam grade, supplementary flag,
  retake flag) are reported honestly as *unavailable* rather than fabricated.
* Authorization is always derived from the authenticated student record, never
  from a browser-supplied id.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import Course, CourseOffering, Department, Enrollment, Grade, Semester, Student

# --------------------------------------------------------------------------- #
# Field availability
# --------------------------------------------------------------------------- #
# The source database has no columns for these institutional concepts. We map
# everything that exists and mark the rest as unavailable so the table renders
# an em dash (—) instead of inventing data.
UNAVAILABLE = "—"

# Course "type" is stored in the course description as e.g. "… (Major core, core)."
# We surface a Course Type derived from the description when present.
PAGE_SIZES = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 10


@dataclass
class RecordRow:
    course_name: str
    course_code: str
    credits: int
    academic_year: str
    semester: str
    final_grade: str
    makeup_grade: str
    supplementary: str
    retake: str
    course_type: str
    offering_faculty: str
    status: str
    enrollment_status: str
    remarks: str
    letter: str
    is_graded: bool


@dataclass
class RecordsPage:
    rows: list[RecordRow] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    pages: int = 1

    @property
    def start(self) -> int:
        return (self.page - 1) * self.page_size + 1 if self.total else 0

    @property
    def end(self) -> int:
        return min(self.page * self.page_size, self.total)


def _course_type(course: Course) -> str:
    """Derive a human course type from the stored description, if possible."""
    desc = (course.description or "").strip()
    if "(" in desc and desc.endswith(")"):
        inner = desc[desc.rfind("(") + 1:-1]
        return inner.split(",")[0].strip().title() or UNAVAILABLE
    return UNAVAILABLE


def _status_for(grade: Grade | None, enrollment_status: str) -> str:
    """Derive an honest academic status from what is actually recorded.

    The institution's pass mark is 60 (documented in the seed/algorithms).
    We only claim a status we can support: Passed / Failed when a grade exists,
    otherwise Pending / Not graded / Withdrawn / Rejected from the enrollment.
    """
    if grade is not None and grade.is_published and grade.score is not None:
        return "Passed" if grade.score >= Decimal("60") else "Failed"
    if enrollment_status == "pending":
        return "Pending"
    if enrollment_status == "dropped":
        return "Withdrawn"
    if enrollment_status == "rejected":
        return "Rejected"
    if enrollment_status == "enrolled":
        return "Not graded"
    if enrollment_status == "completed":
        return "Not graded"
    return UNAVAILABLE


def get_student_for_user(user_id: int) -> Student | None:
    return db.session.execute(
        select(Student).where(Student.user_id == user_id)
    ).scalars().first()


def available_years(student_id: int) -> list[str]:
    """Distinct academic years in which the student has records, newest first."""
    rows = db.session.execute(
        select(Semester.academic_year)
        .join(CourseOffering, CourseOffering.semester_id == Semester.id)
        .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
        .where(Enrollment.student_id == student_id)
        .distinct()
    ).scalars().all()
    return sorted(rows, reverse=True)


def available_terms(student_id: int, academic_year: str | None) -> list[Semester]:
    q = (
        select(Semester)
        .join(CourseOffering, CourseOffering.semester_id == Semester.id)
        .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
        .where(Enrollment.student_id == student_id)
        .distinct()
        .order_by(Semester.start_date)
    )
    if academic_year:
        q = q.where(Semester.academic_year == academic_year)
    return db.session.execute(q).scalars().all()


def _base_query(student_id: int):
    return (
        select(Enrollment, Grade, CourseOffering, Course, Semester, Department)
        .join(CourseOffering, Enrollment.offering_id == CourseOffering.id)
        .join(Course, CourseOffering.course_id == Course.id)
        .join(Semester, CourseOffering.semester_id == Semester.id)
        .outerjoin(Department, Course.department_id == Department.id)
        .outerjoin(Grade, Grade.enrollment_id == Enrollment.id)
        .where(Enrollment.student_id == student_id)
    )


SORT_KEYS = {
    "course_name": "name",
    "course_code": "code",
    "credits": "credits",
    "final_grade": "grade",
    "makeup_grade": "makeup",
    "academic_year": "year",
    "semester": "semester",
}


def get_records(
    student_id: int,
    *,
    academic_year: str | None = None,
    term: str | None = None,
    search: str = "",
    course_type: str | None = None,
    grade_status: str | None = None,
    sort: str = "course_code",
    direction: str = "asc",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> RecordsPage:
    """Return a filtered, sorted, paginated page of academic records.

    All filtering/sorting/pagination is performed in Python after a single
    joined fetch. The dataset per student is small (a few dozen rows), so this
    keeps the query simple and correct without extra DB machinery.
    """
    rows: list[RecordRow] = []
    for enr, grade, offering, course, semester, dept in db.session.execute(
        _base_query(student_id)
    ).all():
        rows.append(RecordRow(
            course_name=course.title,
            course_code=course.code,
            credits=course.credits,
            academic_year=semester.academic_year,
            semester=f"{semester.term.title()}",
            final_grade=(f"{grade.score:g}" if (grade and grade.score is not None) else UNAVAILABLE),
            makeup_grade=UNAVAILABLE,           # not stored by the institution
            supplementary=UNAVAILABLE,          # not stored by the institution
            retake=UNAVAILABLE,                 # not stored by the institution
            course_type=_course_type(course),
            offering_faculty=(dept.name if dept else UNAVAILABLE),
            status=_status_for(grade, enr.status),
            enrollment_status=enr.status,
            remarks=(grade.remarks if grade and grade.remarks else ""),
            letter=(grade.letter if grade and grade.letter else UNAVAILABLE),
            is_graded=bool(grade and grade.is_published and grade.score is not None),
        ))

    # ---- filters ----
    if academic_year:
        rows = [r for r in rows if r.academic_year == academic_year]
    if term:
        rows = [r for r in rows if r.semester.lower() == term.lower()]
    if course_type:
        rows = [r for r in rows if r.course_type.lower() == course_type.lower()]
    if grade_status:
        gs = grade_status.lower()
        if gs == "graded":
            rows = [r for r in rows if r.is_graded]
        elif gs == "pending":
            rows = [r for r in rows if not r.is_graded]
    if search:
        s = search.strip().lower()
        rows = [r for r in rows if s in r.course_name.lower() or s in r.course_code.lower()]

    # ---- sort ----
    reverse = direction == "desc"
    key = sort if sort in SORT_KEYS else "course_code"

    def sort_val(r: RecordRow):
        if key == "course_name":
            return r.course_name.lower()
        if key == "credits":
            return r.credits
        if key == "final_grade":
            # numeric grades sort numerically; em dash sorts last
            try:
                return float(r.final_grade)
            except (TypeError, ValueError):
                return -1.0
        if key == "makeup_grade":
            return r.makeup_grade
        if key == "academic_year":
            return r.academic_year
        if key == "semester":
            return r.semester
        return r.course_code.lower()

    rows.sort(key=sort_val, reverse=reverse)

    # ---- paginate ----
    total = len(rows)
    page_size = page_size if page_size in PAGE_SIZES else DEFAULT_PAGE_SIZE
    pages = max(1, math.ceil(total / page_size)) if total else 1
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    window = rows[start:start + page_size]

    return RecordsPage(rows=window, total=total, page=page, page_size=page_size, pages=pages)


def summary_for(rows_all: list[RecordRow]) -> dict:
    """Summary cards computed from the currently selected (filtered) records."""
    total_courses = len(rows_all)
    total_credits = sum(r.credits for r in rows_all)
    graded = sum(1 for r in rows_all if r.is_graded)
    pending = total_courses - graded
    return {
        "total_courses": total_courses,
        "total_credits": total_credits,
        "graded": graded,
        "pending": pending,
    }
