"""Explainable, deterministic algorithms for USAMIS-Python.

Three conventional rule-based algorithms (enrollment eligibility, academic
performance, fee balance) plus an explainable performance-risk prediction
model (Algorithm 4). Each is pure enough to be unit-tested in isolation and is
integrated through the service layer.
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
from .performance_prediction import (  # noqa: F401
    PredictionResult,
    band_label,
    predict_performance,
    recommended_action,
)

__all__ = [
    "EligibilityResult",
    "evaluate_enrollment",
    "PerformanceResult",
    "calculate_performance",
    "letter_for",
    "DEFAULT_SCALE",
    "FeeResult",
    "calculate_fee_balance",
    "PredictionResult",
    "predict_performance",
    "band_label",
    "recommended_action",
]
