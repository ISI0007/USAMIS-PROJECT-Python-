"""Security tests: password storage, CSRF, and session behaviour."""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.extensions import limiter as _limiter


def test_password_is_hashed_not_plaintext(make_user, app):
    with app.app_context():
        user = make_user(username="hashme", role="student", password="Secret123!")
        assert user.password_hash != "Secret123!"
        assert "Secret123!" not in user.password_hash
        assert user.check_password("Secret123!")
        assert not user.check_password("wrong")


def test_csrf_rejects_post_without_token():
    """A dedicated app with CSRF enabled must reject a token-less POST."""
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
            )
            assert resp.status_code == 400  # CSRF failure
        finally:
            _db.session.remove()
            _db.drop_all()


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
            _db.session.remove()
            _db.drop_all()
            _limiter.reset()
            _limiter.enabled = False


def test_no_stack_trace_on_404(client):
    resp = client.get("/this/does/not/exist")
    assert resp.status_code == 404
    assert b"Traceback" not in resp.data
