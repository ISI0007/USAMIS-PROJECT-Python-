"""Semester and course-offering management."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Course, CourseOffering, Semester, Teacher
from ..security.decorators import permission_required
from ..services import audit
from .forms import OfferingForm, SemesterForm

bp = Blueprint("semesters", __name__, url_prefix="/semesters")


@bp.route("/")
@login_required
def index():
    if not (current_user.has_permission("manage_semesters")
            or current_user.has_permission("view_students")):
        abort(403)
    semesters = db.session.execute(
        db.select(Semester).order_by(Semester.academic_year.desc(), Semester.term)
    ).scalars().all()
    return render_template("semesters/index.html", semesters=semesters)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_semesters")
def create():
    form = SemesterForm()
    if form.validate_on_submit():
        clash = db.session.execute(
            db.select(Semester).where(
                Semester.academic_year == form.academic_year.data.strip(),
                Semester.term == form.term.data)
        ).scalars().first()
        if clash:
            flash("That semester already exists.", "danger")
        else:
            sem = Semester(
                academic_year=form.academic_year.data.strip(),
                term=form.term.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                is_active=form.is_active.data,
                registration_open=form.registration_open.data,
            )
            db.session.add(sem)
            db.session.commit()
            audit.log_action("semester_created", "Semester", sem.id, summary=f"Created {sem.label}")
            db.session.commit()
            flash(f"Semester {sem.label} created.", "success")
            return redirect(url_for("semesters.index"))
    return render_template("semesters/form.html", form=form, semester=None)


@bp.route("/<int:semester_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_semesters")
def edit(semester_id: int):
    sem = db.session.get(Semester, semester_id)
    if sem is None:
        abort(404)
    form = SemesterForm(obj=sem)
    if form.validate_on_submit():
        sem.academic_year = form.academic_year.data.strip()
        sem.term = form.term.data
        sem.start_date = form.start_date.data
        sem.end_date = form.end_date.data
        sem.is_active = form.is_active.data
        sem.registration_open = form.registration_open.data
        db.session.commit()
        audit.log_action("semester_updated", "Semester", sem.id, summary=f"Updated {sem.label}")
        db.session.commit()
        flash("Semester updated.", "success")
        return redirect(url_for("semesters.index"))
    return render_template("semesters/form.html", form=form, semester=sem)


@bp.route("/<int:semester_id>/offerings")
@login_required
def offerings(semester_id: int):
    if not (current_user.has_permission("manage_semesters")
            or current_user.has_permission("view_students")):
        abort(403)
    sem = db.session.get(Semester, semester_id)
    if sem is None:
        abort(404)
    rows = db.session.execute(
        db.select(CourseOffering).where(CourseOffering.semester_id == sem.id)
    ).scalars().all()
    return render_template("semesters/offerings.html", semester=sem, offerings=rows)


@bp.route("/<int:semester_id>/offerings/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_semesters")
def create_offering(semester_id: int):
    sem = db.session.get(Semester, semester_id)
    if sem is None:
        abort(404)
    form = OfferingForm()
    _offering_choices(form)
    if form.validate_on_submit():
        clash = db.session.execute(
            db.select(CourseOffering).where(
                CourseOffering.course_id == form.course_id.data,
                CourseOffering.semester_id == sem.id)
        ).scalars().first()
        if clash:
            flash("That course is already offered this semester.", "danger")
        else:
            offering = CourseOffering(
                course_id=form.course_id.data,
                semester_id=sem.id,
                teacher_id=form.teacher_id.data or None,
                capacity=form.capacity.data,
                is_active=form.is_active.data,
            )
            db.session.add(offering)
            db.session.commit()
            audit.log_action("offering_created", "CourseOffering", offering.id,
                             summary=f"Offering for semester {sem.label}")
            db.session.commit()
            flash("Course offering created.", "success")
            return redirect(url_for("semesters.offerings", semester_id=sem.id))
    return render_template("semesters/offering_form.html", form=form, semester=sem)


@bp.route("/offerings/<int:offering_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_semesters")
def edit_offering(offering_id: int):
    offering = db.session.get(CourseOffering, offering_id)
    if offering is None:
        abort(404)
    form = OfferingForm(obj=offering)
    _offering_choices(form)
    if form.validate_on_submit():
        offering.teacher_id = form.teacher_id.data or None
        offering.capacity = form.capacity.data
        offering.is_active = form.is_active.data
        db.session.commit()
        audit.log_action("offering_updated", "CourseOffering", offering.id,
                         summary="Offering updated")
        db.session.commit()
        flash("Offering updated.", "success")
        return redirect(url_for("semesters.offerings", semester_id=offering.semester_id))
    return render_template("semesters/offering_form.html", form=form,
                           semester=offering.semester, offering=offering)


def _offering_choices(form) -> None:
    form.course_id.choices = [
        (c.id, f"{c.code} — {c.title}")
        for c in db.session.execute(db.select(Course).order_by(Course.code)).scalars().all()
    ]
    form.teacher_id.choices = [(0, "— unassigned —")] + [
        (t.id, f"{t.staff_number} — {t.full_name}")
        for t in db.session.execute(db.select(Teacher).order_by(Teacher.staff_number)).scalars().all()
    ]
