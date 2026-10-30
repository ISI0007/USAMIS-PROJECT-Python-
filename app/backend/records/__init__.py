"""Academic Records: a per-student, tab-like view of every course the student
has taken — course details, semester, grades, status — with search, filters,
sorting and pagination, modelled on the institution's student record layout.

Authorization: the page is always scoped to the authenticated student. Staff
with ``view_students`` may open any student's records via ``?student_id=``.
"""
from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Student
from ..security.decorators import permission_required
from ..services import academic_records_service as records

bp = Blueprint("records", __name__, url_prefix="/records")

SORTABLE = set(records.SORT_KEYS.keys())


@bp.route("/")
@login_required
@permission_required("view_own_grades")
def my_records():
    student = records.get_student_for_user(current_user.id)
    if student is None:
        return render_template("dashboard/no_profile.html")
    return _render(student, own=True)


@bp.route("/student/<int:student_id>")
@login_required
@permission_required("view_students")
def student_records(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    return _render(student, own=False)


def _render(student: Student, *, own: bool):
    args = request.args
    year = (args.get("year") or "").strip() or None
    term = (args.get("term") or "").strip() or None
    search = (args.get("q") or "").strip()
    course_type = (args.get("course_type") or "").strip() or None
    grade_status = (args.get("grade_status") or "").strip() or None

    sort = args.get("sort") or "course_code"
    if sort not in SORTABLE:
        sort = "course_code"
    direction = "desc" if (args.get("dir") or "asc").lower() == "desc" else "asc"
    page = args.get("page", 1, type=int)
    page_size = args.get("page_size", records.DEFAULT_PAGE_SIZE, type=int)
    if page_size not in records.PAGE_SIZES:
        page_size = records.DEFAULT_PAGE_SIZE

    result = records.get_records(
        student.id,
        academic_year=year, term=term, search=search,
        course_type=course_type, grade_status=grade_status,
        sort=sort, direction=direction, page=page, page_size=page_size,
    )

    # Summary reflects the filtered set (all rows, not just the current page).
    all_rows = records.get_records(
        student.id,
        academic_year=year, term=term, search=search,
        course_type=course_type, grade_status=grade_status,
        sort=sort, direction=direction, page=1, page_size=100000,
    )
    summary = records.summary_for(all_rows.rows)

    years = records.available_years(student.id)
    terms = records.available_terms(student.id, year)
    course_types = sorted({r.course_type for r in all_rows.rows if r.course_type != records.UNAVAILABLE})

    return render_template(
        "records/student.html",
        student=student,
        result=result,
        summary=summary,
        years=years,
        terms=terms,
        course_types=course_types,
        f={"year": year, "term": term, "q": search,
           "course_type": course_type, "grade_status": grade_status,
           "sort": sort, "dir": direction, "page_size": page_size},
        sortable=SORTABLE,
        page_sizes=records.PAGE_SIZES,
        unavailable=records.UNAVAILABLE,
        own=own,
    )
