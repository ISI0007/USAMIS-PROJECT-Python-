"""Grade management: entry, publication, and reporting."""
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (Course, CourseOffering, Enrollment, Grade, Semester,
                      Student, Teacher)
from ..security.decorators import permission_required
from ..services import grade_service
from ..services import grade_scale
from .forms import GradeForm

bp = Blueprint("grades", __name__, url_prefix="/grades")


@bp.route("/")
@login_required
@permission_required("view_grades")
def index():
    return redirect(url_for("grades.manage"))


def _gpa_bands():
    """GPA distribution across students (from published grades, 4.0 scale)."""
    rows = db.session.execute(
        db.select(Grade.student_id, Grade.score)
        .where(Grade.is_published.is_(True), Grade.score.isnot(None))
    ).all()
    per_student: dict = {}
    for sid, score in rows:
        pts = grade_scale.points_for_score(score)
        if pts is None:
            continue
        per_student.setdefault(sid, []).append(pts)
    gpas = {sid: sum(v) / len(v) for sid, v in per_student.items() if v}
    bands = [
        ("3.5–4.0", 3.5, 4.01),
        ("3.0–3.5", 3.0, 3.5),
        ("2.5–3.0", 2.5, 3.0),
        ("<2.5", 0.0, 2.5),
    ]
    out = []
    for label, low, high in bands:
        count = sum(1 for g in gpas.values() if low <= g < high)
        out.append({"label": label, "count": count})
    return out, gpas


def _course_pass_rate():
    """Pass rate per course, from published grades (aggregated across offerings)."""
    rows = db.session.execute(
        db.select(Course.code, Course.title, Grade.letter)
        .join(Enrollment, Enrollment.id == Grade.enrollment_id)
        .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
        .join(Course, Course.id == CourseOffering.course_id)
        .where(Grade.is_published.is_(True))
    ).all()
    agg: dict = {}
    for code, title, letter in rows:
        slot = agg.setdefault(code, {"title": title, "pass": 0, "total": 0})
        slot["total"] += 1
        if grade_scale.is_pass(letter):
            slot["pass"] += 1
    out = []
    for code, slot in agg.items():
        if not slot["total"]:
            continue
        rate = round(slot["pass"] / slot["total"] * 100)
        out.append({"code": code, "title": slot["title"], "rate": rate})
    out.sort(key=lambda r: (r["rate"], r["code"]))
    return out


@bp.route("/manage")
@login_required
@permission_required("view_grades")
def manage():
    """Grade Management overview: records, GPA distribution, pass rates."""
    q = (request.args.get("q") or "").strip()

    stmt = (
        db.select(Grade, Student, Course.code, Course.title, Semester)
        .join(Student, Student.id == Grade.student_id)
        .join(Enrollment, Enrollment.id == Grade.enrollment_id)
        .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
        .join(Course, Course.id == CourseOffering.course_id)
        .outerjoin(Semester, Semester.id == CourseOffering.semester_id)
        .order_by(Grade.id.desc())
    )
    rows = db.session.execute(stmt).all()

    records = []
    for grade, student, code, title, semester in rows:
        records.append({
            "id": grade.id,
            "student_number": student.student_number,
            "student_name": student.full_name,
            "course_code": code,
            "course_title": title,
            "score": grade.score,
            "letter": grade.letter,
            "points": grade_scale.points_for_letter(grade.letter),
            "semester": semester.label if semester else "—",
        })
    total_records = len(records)
    if q:
        needle = q.lower()
        records = [r for r in records if needle in r["student_number"].lower()
                   or needle in r["student_name"].lower()
                   or needle in r["course_code"].lower()
                   or needle in (r["course_title"] or "").lower()]

    bands, _gpas = _gpa_bands()
    pass_rates = _course_pass_rate()

    students = db.session.execute(
        db.select(Student).order_by(Student.student_number)).scalars().all()
    offerings = db.session.execute(
        db.select(CourseOffering).join(Course).order_by(Course.code)
    ).scalars().all()
    semesters = db.session.execute(
        db.select(Semester).order_by(Semester.academic_year.desc(), Semester.term)
    ).scalars().all()

    return render_template(
        "grades/manage.html",
        records=records,
        bands=bands,
        pass_rates=pass_rates,
        total_records=total_records,
        students=students,
        offerings=offerings,
        semesters=semesters,
        query=q,
        scale=grade_scale.scale_as_json(),
    )


@bp.route("/manage/enter", methods=["POST"])
@login_required
@permission_required("enter_grades")
def enter():
    """Create a grade from the Enter Grade modal (student + course + score)."""
    student_id = request.form.get("student_id") or ""
    offering_id = request.form.get("offering_id") or ""
    score = request.form.get("score") or ""
    publish = request.form.get("publish") == "on"

    if not student_id.isdigit() or not offering_id.isdigit():
        flash("Select a student and a course.", "danger")
        return redirect(url_for("grades.manage"))

    enrollment = db.session.execute(
        db.select(Enrollment).where(
            Enrollment.student_id == int(student_id),
            Enrollment.offering_id == int(offering_id))
    ).scalars().first()
    if enrollment is None:
        flash("That student is not enrolled in the selected course.", "danger")
        return redirect(url_for("grades.manage"))

    try:
        grade_service.record_grade(current_user, enrollment.id, score, publish=publish)
        flash("Grade saved.", "success")
    except grade_service.GradeError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("grades.manage"))


@bp.route("/record/<int:grade_id>", methods=["POST"])
@login_required
@permission_required("enter_grades")
def update_record(grade_id: int):
    """Edit an existing grade from the records table (score -> letter/points)."""
    grade = db.session.get(Grade, grade_id)
    if grade is None:
        abort(404)
    try:
        grade_service.record_grade(
            current_user, grade.enrollment_id,
            request.form.get("score"),
            publish=request.form.get("publish") == "on",
        )
        flash("Grade updated.", "success")
    except grade_service.GradeError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("grades.manage"))


@bp.route("/offering/<int:offering_id>", methods=["GET", "POST"])
@login_required
@permission_required("enter_grades")
def entry(offering_id: int):
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    if not grade_service.teacher_teaches(current_user, offering):
        abort(403)

    form = GradeForm()
    if form.validate_on_submit():
        try:
            grade_service.record_grade(
                current_user,
                form.enrollment_id.data,
                form.score.data,
                publish=form.publish.data,
                remarks=form.remarks.data or "",
            )
            flash("Grade saved.", "success")
        except grade_service.GradeError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("grades.entry", offering_id=offering.id))

    enrollments = db.session.execute(
        db.select(Enrollment).where(
            Enrollment.offering_id == offering.id,
            Enrollment.status.in_(("enrolled", "completed")))
    ).scalars().all()
    return render_template("grades/entry.html", offering=offering, enrollments=enrollments,
                           form=form)


@bp.route("/enrollment/<int:enrollment_id>", methods=["POST"])
@login_required
@permission_required("enter_grades")
def save(enrollment_id: int):
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None:
        abort(404)
    offering = db.session.get(CourseOffering, enrollment.offering_id)
    if not grade_service.teacher_teaches(current_user, offering):
        abort(403)
    try:
        grade_service.record_grade(
            current_user,
            enrollment_id,
            request.form.get("score"),
            publish=request.form.get("publish") == "on",
        )
        flash("Grade saved.", "success")
    except grade_service.GradeError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("grades.entry", offering_id=offering.id))


@bp.route("/my")
@login_required
@permission_required("view_own_grades")
def my_grades():
    student = db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()
    if student is None:
        return render_template("dashboard/no_profile.html")

    grades = db.session.execute(
        db.select(Grade).where(Grade.student_id == student.id, Grade.is_published.is_(True))
    ).scalars().all()

    records = [
        {
            "course_code": g.enrollment.offering.course.code,
            "credits": g.enrollment.offering.course.credits,
            "score": g.score,
            "published": g.is_published,
        }
        for g in grades
    ]
    from ..algorithms.academic_performance import calculate_performance
    from flask import current_app

    performance = calculate_performance(
        records, gpa_enabled=current_app.config.get("GPA_ENABLED", False)
    )
    return render_template("grades/my.html", grades=grades, performance=performance)
