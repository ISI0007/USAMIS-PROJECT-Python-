"""Student management: list, create, edit, profile."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import AcademicProgram, Department, Enrollment, Student, User
from ..security.decorators import permission_required
from ..services import audit
from .forms import StudentForm

bp = Blueprint("students", __name__, url_prefix="/students")


@bp.route("/")
@login_required
@permission_required("view_students")
def index():
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status") or ""

    query = db.select(Student)
    if q:
        like = f"%{q}%"
        query = query.where(or_(
            Student.student_number.ilike(like),
            Student.first_name.ilike(like),
            Student.last_name.ilike(like),
            Student.email.ilike(like),
        ))
    if status:
        query = query.where(Student.enrollment_status == status)

    pagination = db.paginate(
        query.order_by(Student.student_number),
        page=page, per_page=15, error_out=False,
    )
    return render_template("students/index.html", pagination=pagination, q=q, status=status)


@bp.route("/<int:student_id>")
@login_required
def profile(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)

    # Ownership: a student may only view their own profile.
    if current_user.role == "student":
        own = db.session.execute(
            db.select(Student).where(Student.user_id == current_user.id)
        ).scalars().first()
        if own is None or own.id != student.id:
            abort(403)
    elif not current_user.has_permission("view_students"):
        abort(403)

    enrollments = db.session.execute(
        db.select(Enrollment).where(Enrollment.student_id == student.id)
    ).scalars().all()
    return render_template("students/profile.html", student=student, enrollments=enrollments)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_students")
def create():
    form = StudentForm()
    _populate_choices(form)
    if form.validate_on_submit():
        if db.session.execute(
            db.select(Student).where(Student.student_number == form.student_number.data.strip())
        ).scalars().first():
            flash("That student number is already in use.", "danger")
        else:
            student = Student(
                student_number=form.student_number.data.strip(),
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=form.email.data.strip() if form.email.data else None,
                phone=form.phone.data.strip() if form.phone.data else None,
                address=form.address.data.strip() if form.address.data else None,
                date_of_birth=form.date_of_birth.data,
                department_id=form.department_id.data or None,
                program_id=form.program_id.data or None,
                admission_date=form.admission_date.data,
                enrollment_status=form.enrollment_status.data,
            )
            db.session.add(student)
            db.session.commit()
            audit.log_action("student_created", "Student", student.id,
                             summary=f"Created {student.student_number}")
            db.session.commit()
            flash(f"Student {student.student_number} created.", "success")
            return redirect(url_for("students.profile", student_id=student.id))
    return render_template("students/form.html", form=form, student=None)


@bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_students")
def edit(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)

    form = StudentForm(obj=student)
    _populate_choices(form)
    if form.validate_on_submit():
        student.first_name = form.first_name.data.strip()
        student.last_name = form.last_name.data.strip()
        student.email = form.email.data.strip() if form.email.data else None
        student.phone = form.phone.data.strip() if form.phone.data else None
        student.address = form.address.data.strip() if form.address.data else None
        student.date_of_birth = form.date_of_birth.data
        student.department_id = form.department_id.data or None
        student.program_id = form.program_id.data or None
        student.admission_date = form.admission_date.data
        student.enrollment_status = form.enrollment_status.data
        db.session.commit()
        audit.log_action("student_updated", "Student", student.id,
                         summary=f"Updated {student.student_number}")
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("students.profile", student_id=student.id))
    return render_template("students/form.html", form=form, student=student)


@bp.route("/<int:student_id>/deactivate", methods=["POST"])
@login_required
@permission_required("manage_students")
def deactivate(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    student.enrollment_status = "withdrawn"
    db.session.commit()
    audit.log_action("student_deactivated", "Student", student.id,
                     summary=f"Deactivated {student.student_number}")
    db.session.commit()
    flash("Student marked as withdrawn (soft deactivation).", "info")
    return redirect(url_for("students.profile", student_id=student.id))


def _populate_choices(form) -> None:
    form.department_id.choices = [(0, "— none —")] + [
        (d.id, f"{d.code} — {d.name}")
        for d in db.session.execute(db.select(Department).order_by(Department.code)).scalars().all()
    ]
    form.program_id.choices = [(0, "— none —")] + [
        (p.id, f"{p.code} — {p.name}")
        for p in db.session.execute(db.select(AcademicProgram).order_by(AcademicProgram.code)).scalars().all()
    ]
