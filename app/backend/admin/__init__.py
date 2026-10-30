"""Administration: user accounts, roles, and audit-log viewing."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AuditLog, User
from ..security.decorators import admin_required
from ..security.permissions import ROLE_LABELS, ROLE_PERMISSIONS
from ..services import audit
from .forms import UserForm

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLE_CHOICES = [(r, label) for r, label in ROLE_LABELS.items()]
STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive"), ("blocked", "Blocked")]


@bp.route("/")
@login_required
@admin_required
def index():
    counts = {
        "users": db.session.scalar(db.select(db.func.count(User.id))) or 0,
        "audit": db.session.scalar(db.select(db.func.count(AuditLog.id))) or 0,
    }
    return render_template("admin/index.html", counts=counts)


@bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(User).order_by(User.username),
        page=page, per_page=15, error_out=False,
    )
    return render_template("admin/users.html", pagination=pagination,
                           role_labels=ROLE_LABELS)


@bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    form = UserForm()
    form.role.choices = ROLE_CHOICES
    form.status.choices = STATUS_CHOICES
    if form.validate_on_submit():
        if db.session.execute(
            db.select(User).where(User.username == form.username.data.strip())
        ).scalars().first():
            flash("That username is already taken.", "danger")
        else:
            user = User(
                username=form.username.data.strip(),
                email=form.email.data.strip(),
                full_name=form.full_name.data.strip(),
                role=form.role.data,
                status=form.status.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            audit.log_action("user_created", "User", user.id,
                             summary=f"Created {user.username} role={user.role}")
            db.session.commit()
            flash(f"User {user.username} created.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = UserForm(obj=user)
    form.role.choices = ROLE_CHOICES
    form.status.choices = STATUS_CHOICES
    if form.validate_on_submit():
        user.email = form.email.data.strip()
        user.full_name = form.full_name.data.strip()
        user.role = form.role.data
        user.status = form.status.data
        user.is_active_flag = form.status.data == "active"
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        audit.log_action("user_updated", "User", user.id,
                         summary=f"Updated {user.username} role={user.role} status={user.status}")
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, user=user)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))
    user.status = "inactive" if user.status == "active" else "active"
    user.is_active_flag = user.status == "active"
    db.session.commit()
    audit.log_action("user_status_changed", "User", user.id,
                     summary=f"{user.username} -> {user.status}")
    db.session.commit()
    flash(f"User {user.username} is now {user.status}.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/roles")
@login_required
@admin_required
def roles():
    """Read-only view of the RBAC matrix (single source of truth)."""
    return render_template("admin/roles.html", role_permissions=ROLE_PERMISSIONS,
                           role_labels=ROLE_LABELS)


@bp.route("/audit")
@login_required
@admin_required
def audit_log():
    page = request.args.get("page", 1, type=int)
    action = request.args.get("action") or ""
    entity = request.args.get("entity") or ""
    query = db.select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity_type == entity)
    pagination = db.paginate(
        query.order_by(AuditLog.created_at.desc()),
        page=page, per_page=25, error_out=False,
    )
    return render_template("admin/audit.html", pagination=pagination,
                           action=action, entity=entity)
