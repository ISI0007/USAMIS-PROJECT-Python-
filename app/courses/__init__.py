"""Course management."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Course, CourseOffering, Department, Prerequisite
from ..security.decorators import permission_required
from ..services import audit
from .forms import CourseForm

bp = Blueprint("courses", __name__, url_prefix="/courses")


@bp.route("/")
@login_required
def index():
    from flask_login import current_user

    # Course catalogue is an academic-structure module: only roles that manage
    # courses (plus administrators) may browse it. Teachers/finance reach the
    # courses they need through their own graded/assigned views.
    if not current_user.has_permission("manage_courses"):
        abort(403)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(Course).order_by(Course.code),
        page=page, per_page=15, error_out=False,
    )
    return render_template("courses/index.html", pagination=pagination)


@bp.route("/<int:course_id>")
@login_required
def detail(course_id: int):
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404)
    offerings = db.session.execute(
        db.select(CourseOffering).where(CourseOffering.course_id == course.id)
    ).scalars().all()
    # Candidate prerequisite courses: all active courses except this one and
    # those already configured as prerequisites (avoids duplicate options).
    existing_ids = {p.required_course_id for p in course.prerequisites}
    candidate_courses = db.session.execute(
        db.select(Course)
        .where(Course.id != course.id, Course.is_active.is_(True))
        .order_by(Course.code)
    ).scalars().all()
    candidate_courses = [c for c in candidate_courses if c.id not in existing_ids]
    return render_template("courses/detail.html", course=course, offerings=offerings,
                           candidate_courses=candidate_courses)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_courses")
def create():
    form = CourseForm()
    _choices(form)
    if form.validate_on_submit():
        if db.session.execute(
            db.select(Course).where(Course.code == form.code.data.strip().upper())
        ).scalars().first():
            flash("That course code already exists.", "danger")
        else:
            course = Course(
                code=form.code.data.strip().upper(),
                title=form.title.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                credits=form.credits.data,
                department_id=form.department_id.data or None,
                is_active=form.is_active.data,
            )
            db.session.add(course)
            db.session.commit()
            audit.log_action("course_created", "Course", course.id,
                             summary=f"Created {course.code}")
            db.session.commit()
            flash(f"Course {course.code} created.", "success")
            return redirect(url_for("courses.index"))
    return render_template("courses/form.html", form=form, course=None)


@bp.route("/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_courses")
def edit(course_id: int):
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404)
    form = CourseForm(obj=course)
    _choices(form)
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        clash = db.session.execute(
            db.select(Course).where(Course.code == code, Course.id != course.id)
        ).scalars().first()
        if clash:
            flash("That course code is already used by another course.", "danger")
        else:
            course.code = code
            course.title = form.title.data.strip()
            course.description = form.description.data.strip() if form.description.data else None
            course.credits = form.credits.data
            course.department_id = form.department_id.data or None
            course.is_active = form.is_active.data
            db.session.commit()
            audit.log_action("course_updated", "Course", course.id, summary=f"Updated {course.code}")
            db.session.commit()
            flash("Course updated.", "success")
            return redirect(url_for("courses.detail", course_id=course.id))
    return render_template("courses/form.html", form=form, course=course)


@bp.route("/<int:course_id>/prerequisites", methods=["POST"])
@login_required
@permission_required("manage_courses")
def add_prerequisite(course_id: int):
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404)
    required_id = request.form.get("required_course_id", type=int)
    if not required_id or required_id == course.id:
        flash("Select a valid prerequisite course.", "danger")
        return redirect(url_for("courses.detail", course_id=course.id))

    exists = db.session.execute(
        db.select(Prerequisite).where(
            Prerequisite.course_id == course.id,
            Prerequisite.required_course_id == required_id)
    ).scalars().first()
    if exists:
        flash("That prerequisite is already configured.", "info")
    else:
        db.session.add(Prerequisite(course_id=course.id, required_course_id=required_id))
        db.session.commit()
        audit.log_action("prerequisite_added", "Course", course.id,
                         summary=f"{course.code} requires course {required_id}")
        db.session.commit()
        flash("Prerequisite added.", "success")
    return redirect(url_for("courses.detail", course_id=course.id))


def _choices(form) -> None:
    form.department_id.choices = [(0, "— none —")] + [
        (d.id, f"{d.code} — {d.name}")
        for d in db.session.execute(db.select(Department).order_by(Department.code)).scalars().all()
    ]
