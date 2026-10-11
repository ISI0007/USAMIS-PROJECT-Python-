"""Academic program management."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import AcademicProgram, Department
from ..security.decorators import permission_required
from ..services import audit
from .forms import ProgramForm

bp = Blueprint("programs", __name__, url_prefix="/programs")


@bp.route("/")
@login_required
@permission_required("manage_programs")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(AcademicProgram).order_by(AcademicProgram.code),
        page=page, per_page=15, error_out=False,
    )
    return render_template("programs/index.html", pagination=pagination)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_programs")
def create():
    form = ProgramForm()
    _choices(form)
    if form.validate_on_submit():
        clash = db.session.execute(
            db.select(AcademicProgram).where(
                AcademicProgram.department_id == form.department_id.data,
                AcademicProgram.code == form.code.data.strip().upper())
        ).scalars().first()
        if clash:
            flash("That program code already exists in the selected department.", "danger")
        else:
            program = AcademicProgram(
                code=form.code.data.strip().upper(),
                name=form.name.data.strip(),
                department_id=form.department_id.data,
                duration_years=form.duration_years.data,
                total_credits_required=form.total_credits_required.data,
                description=form.description.data.strip() if form.description.data else None,
                is_active=form.is_active.data,
            )
            db.session.add(program)
            db.session.commit()
            audit.log_action("program_created", "AcademicProgram", program.id,
                             summary=f"Created {program.code}")
            db.session.commit()
            flash(f"Program {program.code} created.", "success")
            return redirect(url_for("programs.index"))
    return render_template("programs/form.html", form=form, program=None)


@bp.route("/<int:program_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_programs")
def edit(program_id: int):
    program = db.session.get(AcademicProgram, program_id)
    if program is None:
        abort(404)
    form = ProgramForm(obj=program)
    _choices(form)
    if form.validate_on_submit():
        program.code = form.code.data.strip().upper()
        program.name = form.name.data.strip()
        program.department_id = form.department_id.data
        program.duration_years = form.duration_years.data
        program.total_credits_required = form.total_credits_required.data
        program.description = form.description.data.strip() if form.description.data else None
        program.is_active = form.is_active.data
        db.session.commit()
        audit.log_action("program_updated", "AcademicProgram", program.id,
                         summary=f"Updated {program.code}")
        db.session.commit()
        flash("Program updated.", "success")
        return redirect(url_for("programs.index"))
    return render_template("programs/form.html", form=form, program=program)


def _choices(form) -> None:
    form.department_id.choices = [
        (d.id, f"{d.code} — {d.name}")
        for d in db.session.execute(db.select(Department).order_by(Department.code)).scalars().all()
    ]
