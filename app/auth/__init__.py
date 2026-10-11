"""Authentication blueprint: login, logout, account and password management."""
from datetime import timedelta

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, limiter
from ..models import User, utcnow
from ..security.decorators import is_safe_redirect
from ..security.permissions import Role
from ..services import audit
from .forms import LoginForm, PasswordChangeForm, ProfileForm, RegistrationForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).where(User.username == form.username.data.strip())
        ).scalars().first()

        # Uniform failure message; no user enumeration.
        if user is None or not user.check_password(form.password.data):
            if user is not None:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                max_attempts = current_app.config["LOGIN_MAX_ATTEMPTS"]
                if user.failed_login_count >= max_attempts:
                    minutes = current_app.config["LOGIN_LOCKOUT_MINUTES"]
                    user.locked_until = utcnow() + timedelta(minutes=minutes)
                    audit.log_action("account_locked", "User", user.id,
                                     summary=f"Locked after {max_attempts} failures.")
                db.session.commit()
            audit.log_action("login_failed", "User", getattr(user, "id", None),
                             summary=f"Failed login for '{form.username.data}'.")
            db.session.commit()
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", form=form), 401

        if user.is_locked():
            flash("Account temporarily locked. Try again later.", "danger")
            return render_template("auth/login.html", form=form), 403

        if not user.is_active:
            flash("This account is not active. Contact an administrator.", "warning")
            return render_template("auth/login.html", form=form), 403

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = utcnow()
        db.session.commit()

        login_user(user, remember=False)
        audit.log_action("login_success", "User", user.id, summary="Signed in.")

        nxt = request.args.get("next") or request.form.get("next")
        if is_safe_redirect(nxt):
            return redirect(nxt)
        return redirect(url_for("dashboard.home"))

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    """Public self-registration.

    Newly created accounts are always assigned the STUDENT role and are
    activated immediately so a visitor can explore the student experience.
    Elevated roles (administrator, academic staff, teacher, finance) are
    never self-assignable; only an administrator can grant them.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        # Uniqueness is enforced by the DB, but check first for a friendly error.
        existing = db.session.execute(
            db.select(User).where(
                (User.username == username) | (User.email == email)
            )
        ).scalars().first()
        if existing is not None:
            flash("That username or email is already registered.", "danger")
            return render_template("auth/register.html", form=form), 409

        user = User(
            username=username,
            email=email,
            full_name=form.full_name.data.strip(),
            role=Role.STUDENT,
            status="active",
            is_active_flag=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        audit.log_action("user_registered", "User", user.id,
                         summary=f"Self-registration of '{username}' (student).")
        db.session.commit()

        flash("Account created. You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    audit.log_action("logout", "User", current_user.id, summary="Signed out.")
    db.session.commit()
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        email_owner = db.session.execute(
            db.select(User).where(User.email == form.email.data.strip(),
                                  User.id != current_user.id)
        ).scalars().first()
        if email_owner is not None:
            flash("That email is already in use.", "danger")
        else:
            current_user.email = form.email.data.strip()
            db.session.commit()
            audit.log_action("profile_updated", "User", current_user.id,
                             summary="Profile updated.")
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            audit.log_action("password_changed", "User", current_user.id,
                             summary="Password changed.")
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("dashboard.home"))
    return render_template("auth/password.html", form=form)
