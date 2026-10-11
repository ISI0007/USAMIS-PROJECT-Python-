"""Integration tests: SMS notifications (F1).

Covers the stub provider, the notification service, and the HTTP routes,
including RBAC. All sends go through the development stub — no network I/O.
"""
from decimal import Decimal

import pytest

from app.extensions import db as _db
from app.models import FeeAssessment, FeeCategory, SmsMessage, Student
from app.services import notification_service
from app.services.notification_service import SmsError


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    monkeypatch.setenv("USAMIS_SMS_PROVIDER", "stub")


def _student(db, number="S-1001", phone="+15550000001"):
    s = Student(student_number=number, first_name="Test", last_name="Student",
                enrollment_status="active", phone=phone)
    db.session.add(s)
    db.session.commit()
    return s


def _assess(db, student, code, amount):
    cat = FeeCategory(code=code, name=code, default_amount=Decimal(amount))
    db.session.add(cat)
    db.session.commit()
    db.session.add(FeeAssessment(student_id=student.id, category_id=cat.id,
                                amount=Decimal(amount)))
    db.session.commit()


# --------------------------------------------------------------------------
# Provider + service
# --------------------------------------------------------------------------
def test_stub_provider_returns_deterministic_reference():
    from app.integrations import StubSmsProvider

    provider = StubSmsProvider()
    first = provider.send("+15550000001", "hello")
    second = provider.send("+15550000001", "hello")
    assert first.ok and second.ok
    assert first.reference == second.reference  # deterministic
    assert first.reference.startswith("stub-sms-")


def test_send_sms_persists_sent_message(db, make_user):
    admin = make_user(username="smsadmin", role="administrator")
    msg = notification_service.send_sms(admin, "+15550000002", "Critical update")
    assert msg.status == "sent"
    assert msg.provider == "stub"
    assert msg.sent_at is not None
    assert msg.recipient == "+15550000002"
    assert _db.session.scalar(_db.select(_db.func.count(SmsMessage.id))) == 1


def test_send_sms_rejects_empty_recipient(db, make_user):
    admin = make_user(username="smsadmin2", role="administrator")
    with pytest.raises(SmsError):
        notification_service.send_sms(admin, "", "body")


def test_send_sms_rejects_empty_body(db, make_user):
    admin = make_user(username="smsadmin3", role="administrator")
    with pytest.raises(SmsError):
        notification_service.send_sms(admin, "+15550000003", "   ")


def test_phone_number_is_normalised(db, make_user):
    admin = make_user(username="smsadmin4", role="administrator")
    msg = notification_service.send_sms(admin, " +1 (555) 000-0004 x", "hi")
    assert msg.recipient == "+15550000004"


def test_fee_reminder_composes_balance(db, make_user):
    admin = make_user(username="smsadmin5", role="administrator")
    student = _student(db)
    msg = notification_service.send_fee_reminder(admin, student, Decimal("1234.50"))
    assert msg.category == "fee_reminder"
    assert "1234.50" in msg.body
    assert student.full_name in msg.body


def test_fee_reminder_uses_student_phone(db, make_user):
    admin = make_user(username="smsadmin6", role="administrator")
    student = _student(db, number="S-1002", phone="+15550000099")
    msg = notification_service.send_fee_reminder(admin, student, Decimal("10.00"))
    assert msg.recipient == "+15550000099"
    assert msg.student_id == student.id


# --------------------------------------------------------------------------
# HTTP routes + RBAC
# --------------------------------------------------------------------------
def test_sms_index_requires_login(client):
    resp = client.get("/notifications/sms")
    assert resp.status_code in (302, 401)


def test_finance_can_open_sms_pages(client, login, make_user):
    make_user(username="fin_sms", role="finance")
    login("fin_sms")
    for path in ("/notifications/sms", "/notifications/sms/compose",
                 "/notifications/sms/fee-reminders"):
        assert client.get(path).status_code == 200


def test_student_denied_sms_pages(client, login, make_user):
    make_user(username="stu_sms", role="student")
    login("stu_sms")
    resp = client.get("/notifications/sms")
    assert resp.status_code == 403


def test_compose_sends_message(client, login, make_user, app, db):
    make_user(username="fin_sms2", role="finance")
    login("fin_sms2")
    resp = client.post(
        "/notifications/sms/compose",
        data={"recipient": "+15551234567", "body": "Route test", "student_id": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Message sent to" in resp.data
    with app.app_context():
        assert _db.session.scalar(_db.select(_db.func.count(SmsMessage.id))) == 1


def test_fee_reminder_batch_sends_to_selected_students(client, login, make_user, app, db):
    make_user(username="fin_sms3", role="finance")
    with app.app_context():
        student = _student(db, number="S-2001", phone="+15550002001")
        _assess(db, student, "TUITION2", "500.00")
        sid = student.id

    login("fin_sms3")
    # Landing page lists the defaulter
    page = client.get("/notifications/sms/fee-reminders")
    assert page.status_code == 200
    assert b"S-2001" in page.data

    resp = client.post(
        "/notifications/sms/fee-reminders",
        data={"student_id": [str(sid)]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"sent: 1" in resp.data
    with app.app_context():
        msg = _db.session.scalar(_db.select(SmsMessage))
        assert msg.category == "fee_reminder"
        assert msg.student_id == sid


def test_fee_reminder_skips_students_without_phone(client, login, make_user, app, db):
    make_user(username="fin_sms4", role="finance")
    with app.app_context():
        s = _student(db, number="S-3001", phone=None)
        _assess(db, s, "TUITION3", "100.00")
        sid = s.id

    login("fin_sms4")
    resp = client.post(
        "/notifications/sms/fee-reminders",
        data={"student_id": [str(sid)]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"skipped" in resp.data
