"""USAMIS-Python application package.

University Student Academic Management Information System built with Flask,
SQLAlchemy and PostgreSQL. Uses the application-factory pattern so that
development, testing and production configurations can be created
independently.
"""
import os

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from .config import get_config
from .extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name: str | None = None, config_object=None) -> Flask:
    """Create and configure a Flask application instance.

    :param config_name: optional configuration key (development/testing/
        production). Falls back to the ``FLASK_ENV`` environment variable.
    :param config_object: an already-instantiated configuration object or
        class, primarily used by the test suite.
    """
    app = Flask(__name__, instance_relative_config=True)

    if config_object is not None:
        app.config.from_object(config_object)
    else:
        app.config.from_object(get_config(config_name))

    os.makedirs(app.instance_path, exist_ok=True)

    _init_extensions(app)
    _ensure_schema(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_cli(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Allow automated tooling (screenshot capture, smoke scripts) to disable
    # rate limiting explicitly. Never set this in a real deployment.
    if os.environ.get("USAMIS_DISABLE_RATELIMIT") == "1":
        limiter.enabled = False

    # Models must be imported so SQLAlchemy/Alembic can see them.
    from . import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):  # pragma: no cover - exercised indirectly
        from .models import User

        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import flash, redirect, request, url_for

        flash("Please sign in to continue.", "warning")
        return redirect(url_for("auth.login", next=request.path))


def _ensure_schema(app: Flask) -> None:
    """Idempotently ensure small additive schema changes are present.

    The project keeps an Alembic migration folder, but for tiny additive
    columns (profile photo) a guarded ALTER TABLE is simpler and safe to run
    on every boot: it is a no-op once the column exists. Never drops or
    rewrites data.
    """
    try:
        from sqlalchemy import inspect, text

        with app.app_context():
            engine = db.engine
            inspector = inspect(engine)
            if "users" not in inspector.get_table_names():
                return
            cols = {c["name"] for c in inspector.get_columns("users")}
            if "avatar_path" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255)"))
                app.logger.info("Schema guard: added users.avatar_path")
    except Exception as exc:  # pragma: no cover - boot resilience
        app.logger.warning("Schema guard skipped: %s", exc)


def _register_blueprints(app: Flask) -> None:
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .students import bp as students_bp
    from .departments import bp as departments_bp
    from .programs import bp as programs_bp
    from .courses import bp as courses_bp
    from .semesters import bp as semesters_bp
    from .enrollments import bp as enrollments_bp
    from .grades import bp as grades_bp
    from .attendance import bp as attendance_bp
    from .fees import bp as fees_bp
    from .reports import bp as reports_bp
    from .notifications import bp as notifications_bp
    from .payments import bp as payments_bp
    from .predictions import bp as predictions_bp
    from .parents import bp as parents_bp
    from .admin import bp as admin_bp
    from .records import bp as records_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(programs_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(semesters_bp)
    app.register_blueprint(enrollments_bp)
    app.register_blueprint(grades_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(fees_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(parents_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(records_bp)

    @app.route("/")
    def index():
        from flask import redirect, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("dashboard.home"))
        return redirect(url_for("auth.login"))


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """A missing/expired CSRF token must not dump a raw 'Bad Request'.

        This is almost always an expired or lost session cookie (stale tab,
        server restart, or the browser not storing cookies). Send the visitor
        back to the sign-in page with a clear message and a fresh token.
        """
        from flask import flash, redirect, request, url_for

        app.logger.warning("CSRF failure on %s: %s", request.path, error.description)
        flash(
            "Your session expired or the page was stale. Please sign in again.",
            "warning",
        )
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response


def _register_cli(app: Flask) -> None:
    from .cli import register_cli

    register_cli(app)
