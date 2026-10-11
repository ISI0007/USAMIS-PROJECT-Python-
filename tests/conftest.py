"""Shared pytest fixtures.

The test suite runs against a dedicated PostgreSQL test database
(``usamis_test``) so PostgreSQL-specific behaviour (row locking, numeric
types, check constraints) is exercised. Tables are created and dropped per
session; data is reset per test function.

Set ``TEST_DATABASE_URL`` to override the connection string.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_test",
)

from app import create_app  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.extensions import limiter as _limiter  # noqa: E402


@pytest.fixture(scope="session")
def app():
    application = create_app(config_object=TestingConfig)
    _limiter.enabled = False  # throttling is covered by dedicated tests
    with application.app_context():
        _db.drop_all()
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    """Reset all tables before each test and yield the session."""
    with app.app_context():
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        yield _db
        _db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(db):
    from app.models import User

    def _make(username="user", role="student", password="Test_Pass1!", status="active"):
        user = User(
            username=username,
            email=f"{username}@test.local",
            full_name=username.title(),
            role=role,
            status=status,
            is_active_flag=status == "active",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def login(client):
    def _login(username, password="Test_Pass1!"):
        return client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    return _login
