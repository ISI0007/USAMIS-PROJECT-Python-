"""Unit tests for Algorithm 3 — Fee Balance and Payment Status."""
from decimal import Decimal

import pytest

from app.algorithms.fee_balance import (
    STATUS_NO_CHARGES,
    STATUS_OUTSTANDING,
    STATUS_OVERPAID,
    STATUS_PAID,
    STATUS_PARTIAL,
    calculate_fee_balance,
)


def test_no_charges():
    result = calculate_fee_balance([], [])
    assert result.status == STATUS_NO_CHARGES
    assert result.balance == Decimal("0.00")


def test_fully_paid():
    result = calculate_fee_balance(
        [{"amount": "1000.00"}], [{"amount": "1000.00"}]
    )
    assert result.status == STATUS_PAID
    assert result.balance == Decimal("0.00")


def test_partially_paid():
    result = calculate_fee_balance(
        [{"amount": "1000.00"}], [{"amount": "400.00"}]
    )
    assert result.status == STATUS_PARTIAL
    assert result.balance == Decimal("600.00")


def test_outstanding_unpaid():
    result = calculate_fee_balance([{"amount": "1000.00"}], [])
    assert result.status == STATUS_OUTSTANDING
    assert result.balance == Decimal("1000.00")


def test_adjustment_applied():
    result = calculate_fee_balance(
        [{"amount": "1000.00", "adjustment": "200.00"}], [{"amount": "300.00"}]
    )
    assert result.total_payable == Decimal("800.00")
    assert result.balance == Decimal("500.00")


def test_overpayment_reported_as_credit():
    result = calculate_fee_balance(
        [{"amount": "1000.00"}], [{"amount": "1200.00"}]
    )
    assert result.status == STATUS_OVERPAID
    assert result.credit == Decimal("200.00")
    assert result.balance == Decimal("0.00")


def test_negative_assessment_rejected():
    with pytest.raises(ValueError):
        calculate_fee_balance([{"amount": "-1.00"}], [])


def test_negative_payment_rejected():
    with pytest.raises(ValueError):
        calculate_fee_balance([{"amount": "100.00"}], [{"amount": "-5.00"}])


def test_zero_payment_rejected():
    with pytest.raises(ValueError):
        calculate_fee_balance([{"amount": "100.00"}], [{"amount": "0"}])


def test_adjustment_exceeding_amount_capped():
    result = calculate_fee_balance(
        [{"amount": "100.00", "adjustment": "500.00"}], []
    )
    assert result.total_payable == Decimal("0.00")
    assert any("exceeds" in n.lower() for n in result.notes)


def test_decimal_precision_no_float_error():
    # 0.1 + 0.2 style problem must not appear with Decimal arithmetic.
    result = calculate_fee_balance(
        [{"amount": "0.10"}, {"amount": "0.20"}], [{"amount": "0.30"}]
    )
    assert result.balance == Decimal("0.00")
    assert result.status == STATUS_PAID


def test_multiple_assessments_and_payments():
    result = calculate_fee_balance(
        [{"amount": "500.00"}, {"amount": "300.00", "adjustment": "50.00"}],
        [{"amount": "200.00"}, {"amount": "100.00"}],
    )
    assert result.total_assessed == Decimal("800.00")
    assert result.total_adjustments == Decimal("50.00")
    assert result.total_payable == Decimal("750.00")
    assert result.total_paid == Decimal("300.00")
    assert result.balance == Decimal("450.00")
