"""Department management."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Department
from ..security.decorators import permission_required
from ..services import audit
from .forms import DepartmentForm

bp = Blueprint("departments", __name__, url_prefix="/departments")


@bp.route("/")
@login_required
@permission_required("manage_departments")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(Department).order_by(Department.code),
        page=page, per_page=15, error_out=False,
    )
    return render_template("departments/index.html", pagination=pagination)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_departments")
def create():
    form = DepartmentForm()
    if form.validate_on_submit():
        if db.session.execute(
            db.select(Department).where(Department.code == form.code.data.strip().upper())
        ).scalars().first():
            flash("That department code already exists.", "danger")
        else:
            dept = Department(
                code=form.code.data.strip().upper(),
                name=form.name.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                is_active=form.is_active.data,
            )
            db.session.add(dept)
            db.session.commit()
            audit.log_action("department_created", "Department", dept.id,
                             summary=f"Created {dept.code}")
            db.session.commit()
            flash(f"Department {dept.code} created.", "success")
            return redirect(url_for("departments.index"))
    return render_template("departments/form.html", form=form, department=None)


@bp.route("/<int:department_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_departments")
def edit(department_id: int):
    dept = db.session.get(Department, department_id)
    if dept is None:
        abort(404)
    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        clash = db.session.execute(
            db.select(Department).where(Department.code == code, Department.id != dept.id)
        ).scalars().first()
        if clash:
            flash("That department code is already used by another department.", "danger")
        else:
            dept.code = code
            dept.name = form.name.data.strip()
            dept.description = form.description.data.strip() if form.description.data else None
            dept.is_active = form.is_active.data
            db.session.commit()
            audit.log_action("department_updated", "Department", dept.id,
                             summary=f"Updated {dept.code}")
            db.session.commit()
            flash("Department updated.", "success")
            return redirect(url_for("departments.index"))
    return render_template("departments/form.html", form=form, department=dept)
