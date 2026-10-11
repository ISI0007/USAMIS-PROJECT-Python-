"""Algorithm 3 — Fee Balance and Payment Status.

Outstanding Balance = Total Fees - Valid Payments - Applicable Adjustments

All arithmetic is decimal-safe (``Decimal``); binary floats are never used for
money. Overpayments are reported explicitly rather than shown as a bogus
negative balance.

See ``docs/ALGORITHMS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

STATUS_PAID = "paid"
STATUS_PARTIAL = "partially_paid"
STATUS_OUTSTANDING = "outstanding"
STATUS_OVERPAID = "overpaid"
STATUS_NO_CHARGES = "no_charges"


@dataclass
class FeeResult:
    total_assessed: Decimal
    total_adjustments: Decimal
    total_payable: Decimal
    total_paid: Decimal
    balance: Decimal
    credit: Decimal
    status: str
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total_assessed": str(self.total_assessed),
            "total_adjustments": str(self.total_adjustments),
            "total_payable": str(self.total_payable),
            "total_paid": str(self.total_paid),
            "balance": str(self.balance),
            "credit": str(self.credit),
            "status": self.status,
            "notes": list(self.notes),
        }


def _dec(value) -> Decimal:
    if value is None:
        return ZERO
    try:
        return Decimal(str(value))
    except Exception:
        raise ValueError(f"Invalid monetary value: {value!r}")


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_fee_balance(assessments: list[dict], payments: list[dict]) -> FeeResult:
    """Compute a student's fee position.

    :param assessments: dicts with ``amount`` and optional ``adjustment``.
    :param payments: dicts with ``amount``.

    Invalid inputs (negative amounts) raise ``ValueError`` so callers cannot
    silently record invalid money.
    """
    notes: list[str] = []
    total_assessed = ZERO
    total_adjustments = ZERO

    for a in assessments:
        amount = _dec(a.get("amount"))
        adjustment = _dec(a.get("adjustment", ZERO))
        if amount < 0:
            raise ValueError("Assessment amount cannot be negative.")
        if adjustment < 0:
            raise ValueError("Adjustment cannot be negative.")
        if adjustment > amount:
            notes.append(
                f"Adjustment {adjustment} exceeds assessment {amount}; "
                "net capped at zero."
            )
            adjustment = amount
        total_assessed += amount
        total_adjustments += adjustment

    total_paid = ZERO
    for p in payments:
        amount = _dec(p.get("amount"))
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")
        total_paid += amount

    total_payable = total_assessed - total_adjustments
    if total_payable < ZERO:
        total_payable = ZERO

    balance = total_payable - total_paid
    credit = ZERO
    status: str

    if total_payable == ZERO and total_paid == ZERO:
        status = STATUS_NO_CHARGES
    elif balance > ZERO:
        status = STATUS_PARTIAL if total_paid > ZERO else STATUS_OUTSTANDING
    elif balance == ZERO:
        status = STATUS_PAID
    else:
        credit = _q(-balance)
        balance = ZERO
        status = STATUS_OVERPAID
        notes.append(f"Overpayment of {credit} recorded as a credit balance.")

    return FeeResult(
        total_assessed=_q(total_assessed),
        total_adjustments=_q(total_adjustments),
        total_payable=_q(total_payable),
        total_paid=_q(total_paid),
        balance=_q(balance),
        credit=credit,
        status=status,
        notes=notes,
    )
