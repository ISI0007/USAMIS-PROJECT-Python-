"""Register custom Flask CLI commands.

The seed command is development-only and safe to run repeatedly (idempotent
upserts keyed on natural identifiers).
"""
import datetime as dt

import click
from flask import Flask
from flask.cli import with_appcontext


def register_cli(app: Flask) -> None:
    app.cli.add_command(seed_command)
    app.cli.add_command(seed_java_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(db_status_command)


@click.command("seed")
@click.option("--reset", is_flag=True, help="Delete existing demo data first (development only).")
@with_appcontext
def seed_command(reset: bool) -> None:
    """Populate synthetic development/demo data safely (idempotent)."""
    from .jit_seed import seed_jit_departments
    from .java_seed_bridge import reconcile_java_seed
    from .seed import run_seed

    run_seed(reset=reset)
    seed_jit_departments()
    report = reconcile_java_seed()
    click.echo(f"Seed complete. Java bridge: {report}")


@click.command("seed-java")
@with_appcontext
def seed_java_command() -> None:
    """Reconcile the Java reference roster into the Python database."""
    from .java_seed_bridge import reconcile_java_seed

    report = reconcile_java_seed()
    click.echo(f"Java seed reconciled: {report}")


@click.command("create-admin")
@click.option("--username", required=True)
@click.option("--email", required=True)
@click.option("--password", required=True)
@with_appcontext
def create_admin_command(username: str, email: str, password: str) -> None:
    """Create (or update) an administrator account."""
    from .models import User
    from .extensions import db

    user = db.session.execute(
        db.select(User).where(User.username == username)
    ).scalars().first()
    if user is None:
        user = User(username=username, email=email, full_name="Administrator",
                    role="administrator")
        user.set_password(password)
        db.session.add(user)
    else:
        user.email = email
        user.role = "administrator"
        user.set_password(password)
    db.session.commit()
    click.echo(f"Administrator '{username}' ready.")


@click.command("db-status")
@with_appcontext
def db_status_command() -> None:
    """Report row counts for the main entities."""
    from .extensions import db
    from .models import (
        Course, Department, Enrollment, Grade, Payment, Student, User,
    )

    for model in (User, Student, Department, Course, Enrollment, Grade, Payment):
        count = db.session.query(model).count()
        click.echo(f"{model.__name__:<16} {count}")
