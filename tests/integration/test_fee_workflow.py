"""Integration tests: fee assessment and payment services with decimal money."""
from decimal import Decimal

import pytest

from app.models import FeeCategory, Student
from app.services import fee_service


def _student(db):
    s = Student(student_number="S-0001", first_name="A", last_name="B",
                enrollment_status="active")
    db.session.add(s)
    db.session.commit()
    return s


def _category(db):
    c = FeeCategory(code="TUITION", name="Tuition", default_amount=Decimal("1000.00"))
    db.session.add(c)
    db.session.commit()
    return c


def test_assess_and_pay_updates_balance(db, make_user):
    finance = make_user(username="fin", role="finance")
    student = _student(db)
    category = _category(db)

    fee_service.assess_fee(finance, student, category, Decimal("1000.00"))
    balance = fee_service.student_balance(student)
    assert balance.balance == Decimal("1000.00")
    assert balance.status == "outstanding"

    fee_service.record_payment(finance, student, Decimal("400.00"), reference="R1")
    balance = fee_service.student_balance(student)
    assert balance.balance == Decimal("600.00")
    assert balance.status == "partially_paid"

    fee_service.record_payment(finance, student, Decimal("600.00"), reference="R2")
    balance = fee_service.student_balance(student)
    assert balance.balance == Decimal("0.00")
    assert balance.status == "paid"


def test_duplicate_payment_reference_rejected(db, make_user):
    finance = make_user(username="fin2", role="finance")
    student = _student(db)
    fee_service.record_payment(finance, student, Decimal("100.00"), reference="DUP")
    with pytest.raises(fee_service.FeeError):
        fee_service.record_payment(finance, student, Decimal("50.00"), reference="DUP")


def test_negative_amount_rejected(db, make_user):
    finance = make_user(username="fin3", role="finance")
    student = _student(db)
    with pytest.raises(fee_service.FeeError):
        fee_service.record_payment(finance, student, Decimal("-10.00"))


def test_duplicate_assessment_rejected(db, make_user):
    finance = make_user(username="fin4", role="finance")
    student = _student(db)
    category = _category(db)
    fee_service.assess_fee(finance, student, category, Decimal("500.00"))
    with pytest.raises(fee_service.FeeError):
        fee_service.assess_fee(finance, student, category, Decimal("500.00"))


def test_adjustment_greater_than_amount_rejected(db, make_user):
    finance = make_user(username="fin5", role="finance")
    student = _student(db)
    category = _category(db)
    with pytest.raises(fee_service.FeeError):
        fee_service.assess_fee(finance, student, category, Decimal("100.00"),
                               adjustment=Decimal("200.00"))
