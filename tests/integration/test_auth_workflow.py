"""Integration tests: authentication workflows end to end."""
import pytest

from app.models import User


def test_login_page_renders(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"USAMIS" in resp.data


def test_login_with_valid_credentials(client, make_user, app):
    with app.app_context():
        user = make_user(username="validuser", role="student")
        uid = user.id
    resp = client.post(
        "/auth/login",
        data={"username": "validuser", "password": "Test_Pass1!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'action="/auth/logout"' in resp.data
    with app.app_context():
        refreshed = app.extensions["sqlalchemy"].session.get(User, uid)
        assert refreshed.last_login_at is not None


def test_login_invalid_password_rejected(client, make_user, app):
    with app.app_context():
        make_user(username="badpass", role="student")
    resp = client.post(
        "/auth/login",
        data={"username": "badpass", "password": "wrong"},
        follow_redirects=True,
    )
    assert resp.status_code == 401
    assert b"Invalid username or password" in resp.data


def test_login_unknown_user_rejected(client):
    resp = client.post(
        "/auth/login",
        data={"username": "ghost", "password": "whatever"},
        follow_redirects=True,
    )
    assert resp.status_code == 401


def test_inactive_account_cannot_login(client, make_user, app):
    with app.app_context():
        make_user(username="inactive1", role="student", status="inactive")
    resp = client.post(
        "/auth/login",
        data={"username": "inactive1", "password": "Test_Pass1!"},
        follow_redirects=True,
    )
    assert resp.status_code == 403


def test_blocked_account_cannot_login(client, make_user, app):
    with app.app_context():
        make_user(username="blocked1", role="student", status="blocked")
    resp = client.post(
        "/auth/login",
        data={"username": "blocked1", "password": "Test_Pass1!"},
        follow_redirects=True,
    )
    assert resp.status_code == 403


def test_logout_clears_session(client, make_user, app):
    with app.app_context():
        make_user(username="logmeout", role="student")
    client.post("/auth/login", data={"username": "logmeout", "password": "Test_Pass1!"})
    resp = client.post("/auth/logout", follow_redirects=True)
    assert resp.status_code == 200
    # After logout the dashboard must redirect to login.
    protected = client.get("/dashboard/", follow_redirects=False)
    assert protected.status_code == 302


def test_failed_login_is_audited(client, make_user, app):
    from app.models import AuditLog

    with app.app_context():
        make_user(username="auditme", role="student")
    client.post("/auth/login", data={"username": "auditme", "password": "nope"})
    with app.app_context():
        count = app.extensions["sqlalchemy"].session.query(AuditLog).filter_by(
            action="login_failed"
        ).count()
        assert count >= 1
