"""Explainable, deterministic algorithms for USAMIS-Python.

These are conventional rule-based algorithms — not AI/ML. Each is pure enough
to be unit-tested in isolation and is integrated through the service layer.
"""
from .enrollment_eligibility import (  # noqa: F401
    EligibilityResult,
    evaluate_enrollment,
)
from .academic_performance import (  # noqa: F401
    DEFAULT_SCALE,
    PerformanceResult,
    calculate_performance,
    letter_for,
)
from .fee_balance import FeeResult, calculate_fee_balance  # noqa: F401

__all__ = [
    "EligibilityResult",
    "evaluate_enrollment",
    "PerformanceResult",
    "calculate_performance",
    "letter_for",
    "DEFAULT_SCALE",
    "FeeResult",
    "calculate_fee_balance",
]
