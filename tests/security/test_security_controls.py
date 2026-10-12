"""Security tests: password storage, CSRF, and session behaviour.

NOTE ON ISOLATION
-----------------
``_db`` is a module-level SQLAlchemy singleton shared by every app instance,
and the schema itself is owned by the session-scoped ``app`` fixture in
``conftest.py``. Several tests here build their own app to toggle CSRF or the
rate limiter. Those tests must therefore NEVER leave the shared schema
dropped -- a bare ``_db.drop_all()`` would delete the tables out from under
the session fixture and every later test would fail with
``relation "..." does not exist``. They re-create the schema in teardown
instead, so the next test always starts from a valid, empty database.
"""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.extensions import limiter as _limiter


def _reset_schema() -> None:
    """Leave the shared schema present and empty for the next test."""
    _db.session.remove()
    _db.drop_all()
    _db.create_all()


def test_password_is_hashed_not_plaintext(make_user, app):
    with app.app_context():
        user = make_user(username="hashme", role="student", password="Secret123!")
        assert user.password_hash != "Secret123!"
        assert "Secret123!" not in user.password_hash
        assert user.check_password("Secret123!")
        assert not user.check_password("wrong")


def test_csrf_rejects_post_without_token():
    """A dedicated app with CSRF enabled must reject a token-less POST.

    The request is still *rejected* (it must never authenticate or mutate
    state); the app now redirects to the sign-in page with a warning instead
    of dumping a raw 'Bad Request', so a stale session is recoverable.
    """
    app = create_app(config_object=TestingConfig)
    app.config["WTF_CSRF_ENABLED"] = True
    _limiter.enabled = False
    with app.app_context():
        _db.create_all()
        try:
            client = app.test_client()
            resp = client.post(
                "/auth/login",
                data={"username": "x", "password": "y"},
                follow_redirects=False,
            )
            # Rejected: redirect to login (not 400, and never a success).
            assert resp.status_code in (302, 400)
            if resp.status_code == 302:
                assert "/auth/login" in resp.headers.get("Location", "")
        finally:
            _reset_schema()


def test_csrf_redirect_lands_on_login_with_warning():
    """Following the CSRF redirect shows the sign-in page plus a warning."""
    app = create_app(config_object=TestingConfig)
    app.config["WTF_CSRF_ENABLED"] = True
    _limiter.enabled = False
    with app.app_context():
        _db.create_all()
        try:
            client = app.test_client()
            resp = client.post(
                "/auth/login",
                data={"username": "x", "password": "y"},
                follow_redirects=True,
            )
            assert resp.status_code == 200
            body = resp.get_data(as_text=True)
            assert "session expired" in body.lower()
        finally:
            _reset_schema()


def test_login_throttle_enforced(monkeypatch):
    """Repeated failed logins from one address are throttled (429)."""
    app = create_app(config_object=TestingConfig)
    _limiter.enabled = True
    _limiter.reset()
    with app.app_context():
        _db.create_all()
        try:
            client = app.test_client()
            statuses = []
            for _ in range(25):
                r = client.post("/auth/login",
                                data={"username": "nobody", "password": "x"})
                statuses.append(r.status_code)
            assert 429 in statuses, "expected rate limiting to trigger"
        finally:
            _reset_schema()
            _limiter.reset()
            _limiter.enabled = False


def test_no_stack_trace_on_404(client):
    resp = client.get("/this/does/not/exist")
    assert resp.status_code == 404
    assert b"Traceback" not in resp.data
