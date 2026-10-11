"""Integration tests: online payment gateway (F2).

Covers the stub provider, intent creation/confirmation, idempotency, state
transitions, and the HTTP routes (student + finance) including RBAC.
"""
from decimal import Decimal

import pytest

from app.extensions import db as _db
from app.models import FeeAssessment, FeeCategory, Payment, PaymentIntent, Student
from app.services import fee_service, payment_gateway_service
from app.services.payment_gateway_service import PaymentGatewayError


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    monkeypatch.setenv("USAMIS_PAYMENT_PROVIDER", "stub")


def _student(db, number="P-1001"):
    s = Student(student_number=number, first_name="Pay", last_name="Student",
                enrollment_status="active", phone="+15550007001")
    db.session.add(s)
    db.session.commit()
    return s


def _assess(db, student, code="GATEWAY", amount="300.00"):
    cat = FeeCategory(code=code, name=code, default_amount=Decimal(amount))
    db.session.add(cat)
    db.session.commit()
    db.session.add(FeeAssessment(student_id=student.id, category_id=cat.id,
                                amount=Decimal(amount)))
    db.session.commit()


# --------------------------------------------------------------------------
# Provider + service
# --------------------------------------------------------------------------
def test_stub_payment_provider_returns_checkout_url():
    from app.integrations import StubPaymentProvider

    provider = StubPaymentProvider()
    result = provider.create_intent(reference="PAY-TEST", amount=Decimal("10.00"))
    assert result.ok
    assert result.provider_ref.startswith("stub-pi-")
    assert result.checkout_url.startswith(StubPaymentProvider.URL_PREFIX)
    assert provider.verify(result.provider_ref) is True


def test_start_intent_creates_pending_row(db, make_user):
    finance = make_user(username="pay_fin", role="finance")
    student = _student(db)
    intent = payment_gateway_service.start_intent(finance, student, "25.00")
    assert intent.status == "pending"
    assert intent.provider == "stub"
    assert intent.checkout_url
    assert intent.reference.startswith("PAY-")
    assert _db.session.scalar(_db.select(_db.func.count(PaymentIntent.id))) == 1


def test_start_intent_rejects_zero_amount(db, make_user):
    finance = make_user(username="pay_fin2", role="finance")
    student = _student(db)
    with pytest.raises(fee_service.FeeError):
        payment_gateway_service.start_intent(finance, student, "0")


def test_confirm_intent_records_payment_and_updates_balance(db, make_user):
    finance = make_user(username="pay_fin3", role="finance")
    student = _student(db)
    _assess(db, student)
    before = fee_service.student_balance(student).balance

    intent = payment_gateway_service.start_intent(finance, student, "50.00")
    payment_gateway_service.confirm_intent(finance, intent)

    _db.session.refresh(intent)
    assert intent.status == "paid"
    assert intent.payment_id is not None
    after = fee_service.student_balance(student).balance
    assert after == before - Decimal("50.00")


def test_confirm_is_idempotent(db, make_user):
    finance = make_user(username="pay_fin4", role="finance")
    student = _student(db)
    _assess(db, student)

    intent = payment_gateway_service.start_intent(finance, student, "50.00")
    payment_gateway_service.confirm_intent(finance, intent)
    after_first = fee_service.student_balance(student).balance

    payment_gateway_service.confirm_intent(finance, intent)  # repeat
    after_second = fee_service.student_balance(student).balance
    assert after_first == after_second
    n = _db.session.scalar(
        _db.select(_db.func.count(Payment.id)).where(
            Payment.reference == intent.reference)
    )
    assert n == 1


def test_invalid_transition_rejected(db, make_user):
    finance = make_user(username="pay_fin5", role="finance")
    student = _student(db)
    intent = payment_gateway_service.start_intent(finance, student, "10.00")
    payment_gateway_service.confirm_intent(finance, intent)
    with pytest.raises(PaymentGatewayError):
        payment_gateway_service._transition(intent, "pending")


def test_fail_intent_marks_failed(db, make_user):
    finance = make_user(username="pay_fin6", role="finance")
    student = _student(db)
    intent = payment_gateway_service.start_intent(finance, student, "10.00")
    payment_gateway_service.fail_intent(finance, intent, "card declined")
    _db.session.refresh(intent)
    assert intent.status == "failed"
    assert "declined" in intent.error


# --------------------------------------------------------------------------
# HTTP routes + RBAC
# --------------------------------------------------------------------------
def test_payments_index_requires_login(client):
    assert client.get("/payments/").status_code in (302, 401)


def test_student_denied_finance_payments_index(client, login, make_user):
    make_user(username="pay_stu", role="student")
    login("pay_stu")
    assert client.get("/payments/").status_code == 403


def test_finance_can_open_payments_index(client, login, make_user):
    make_user(username="pay_fin7", role="finance")
    login("pay_fin7")
    assert client.get("/payments/").status_code == 200


def test_full_http_flow_start_then_callback(client, login, make_user, app, db):
    """Student starts a payment, then the stub callback settles it."""
    from app.models import User

    with app.app_context():
        student = _student(db, number="P-2001")
        _assess(db, student, code="GATEWAY2")
        # link a student login to this student
        user = User(username="pay_student2", email="p2@test.local",
                    full_name="P Two", role="student", status="active",
                    is_active_flag=True)
        user.set_password("Test_Pass1!")
        db.session.add(user)
        db.session.commit()
        student.user_id = user.id
        db.session.commit()
        sid = student.id

    login("pay_student2")

    # landing page shows the pay form
    page = client.get("/payments/my")
    assert page.status_code == 200
    assert b"/payments/start" in page.data

    # start a payment
    resp = client.post("/payments/start", data={"amount": "40.00"},
                       follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert "/checkout" in location
    intent_id = int(location.rstrip("/").split("/")[-2])

    # callback confirms it
    with app.app_context():
        intent = _db.session.get(PaymentIntent, intent_id)
        reference = intent.reference
    cb = client.post("/payments/callback", data={"reference": reference},
                     follow_redirects=True)
    assert cb.status_code == 200
    assert b"Payment confirmed" in cb.data

    with app.app_context():
        intent = _db.session.get(PaymentIntent, intent_id)
        assert intent.status == "paid"
        assert intent.student_id == sid


def test_callback_unknown_reference_404(client, db):
    resp = client.post("/payments/callback", data={"reference": "PAY-NOPE"})
    assert resp.status_code == 404


def test_checkout_denied_for_other_student(client, login, make_user, app, db):
    """A student must not view another student's checkout page."""
    from app.models import User

    with app.app_context():
        owner = _student(db, number="P-3001")
        _assess(db, owner, code="GATEWAY3")
        intent = payment_gateway_service.start_intent(
            None, owner, "15.00")
        intent_id = intent.id

        other = User(username="pay_other", email="o@test.local",
                     full_name="O Other", role="student", status="active",
                     is_active_flag=True)
        other.set_password("Test_Pass1!")
        db.session.add(other)
        db.session.commit()

    login("pay_other")
    assert client.get(f"/payments/{intent_id}/checkout").status_code == 403
