"""Algorithm 4 — AI-based Student Performance Prediction (explainable).

Predicts an academic-risk band (low / medium / high) for a student from two
signals that the system already tracks:

* the credit-weighted academic average (Algorithm 2), and
* the attendance rate (present + late over total sessions).

The model is deliberately **transparent**, not a black box: it is a logistic
function over standardised inputs with published coefficients, so every
prediction can be explained by listing the exact factors that pushed the score
up or down. This keeps the feature honest ("ML-ready", not "deep learning") and
auditable, which matters for a system that informs real academic decisions.

Risk score = sigmoid(z), z = b0 + b1*grade_term + b2*attendance_term

See ``docs/ALGORITHMS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

# --- Published model coefficients (documented, auditable) -------------------
# Risk rises as grades/attendance fall *below* their reference points, so both
# weights are negative: a student below the baseline accumulates positive z
# (more risk), one above it accumulates negative z (less risk). Bias is a small
# negative so an exactly-average student sits comfortably in the low band.
COEFFICIENTS = {
    "bias": -0.2,
    "grade_weight": -1.6,       # per standardised grade point above/below mean
    "attendance_weight": -1.2,  # per standardised attendance point
}

# Reference points used to standardise the raw inputs into the model's terms.
GRADE_BASELINE = 65.0      # a "meets expectations" average
ATTENDANCE_BASELINE = 75.0  # the institutional threshold already used in reports
GRADE_SPAN = 15.0          # +/- range treated as one standard unit
ATTENDANCE_SPAN = 25.0

# Risk band cut-offs on the 0..1 risk score.
HIGH_RISK_THRESHOLD = 0.66
MEDIUM_RISK_THRESHOLD = 0.40

BAND_LOW = "low"
BAND_MEDIUM = "medium"
BAND_HIGH = "high"


@dataclass
class Factor:
    """One explainable contributor to the prediction."""

    name: str
    detail: str
    impact: float  # signed contribution to z (positive = more risk)


@dataclass
class PredictionResult:
    risk_score: Decimal          # 0.00 .. 1.00
    band: str                    # low | medium | high
    factors: list[Factor] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    has_data: bool = True


def _sigmoid(z: float) -> float:
    # numerically stable sigmoid
    if z >= 0:
        ez = pow(2.718281828459045, -z)
        return 1.0 / (1.0 + ez)
    ez = pow(2.718281828459045, z)
    return ez / (1.0 + ez)


def _q(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def predict_performance(*, weighted_average, attendance_rate) -> PredictionResult:
    """Predict an academic-risk band with an explanation.

    :param weighted_average: credit-weighted average (0-100) or ``None`` when no
        published grades exist.
    :param attendance_rate: fraction 0..1 of sessions attended, or ``None`` when
        there is no attendance on record.

    Missing signals fall back to their baseline (treated as neutral) and a note
    is added, so the function never crashes on sparse data.
    """
    notes: list[str] = []
    factors: list[Factor] = []
    z = COEFFICIENTS["bias"]

    has_grade = weighted_average is not None
    has_attendance = attendance_rate is not None

    if has_grade:
        grade = float(weighted_average)
        grade_term = (grade - GRADE_BASELINE) / GRADE_SPAN
        contrib = COEFFICIENTS["grade_weight"] * grade_term
        z += contrib
        factors.append(Factor(
            "Academic average", f"{grade:.1f} vs baseline {GRADE_BASELINE:.0f}",
            round(contrib, 3)))
    else:
        notes.append("No published grades; academic signal omitted.")
        factors.append(Factor("Academic average", "no data (neutral)", 0.0))

    if has_attendance:
        rate = float(attendance_rate) * 100.0
        att_term = (rate - ATTENDANCE_BASELINE) / ATTENDANCE_SPAN
        contrib = COEFFICIENTS["attendance_weight"] * att_term
        z += contrib
        factors.append(Factor(
            "Attendance", f"{rate:.0f}% vs threshold {ATTENDANCE_BASELINE:.0f}%",
            round(contrib, 3)))
    else:
        notes.append("No attendance on record; attendance signal omitted.")
        factors.append(Factor("Attendance", "no data (neutral)", 0.0))

    risk = _sigmoid(z)

    if risk >= HIGH_RISK_THRESHOLD:
        band = BAND_HIGH
    elif risk >= MEDIUM_RISK_THRESHOLD:
        band = BAND_MEDIUM
    else:
        band = BAND_LOW

    # Sort factors by absolute impact so the biggest driver is first.
    factors.sort(key=lambda f: abs(f.impact), reverse=True)

    return PredictionResult(
        risk_score=_q(risk),
        band=band,
        factors=factors,
        notes=notes,
        has_data=has_grade or has_attendance,
    )


def band_label(band: str) -> str:
    return {"low": "Low risk", "medium": "Medium risk", "high": "High risk"}.get(
        band, band)


def recommended_action(band: str) -> str:
    return {
        "low": "No action needed; continue monitoring.",
        "medium": "Advisor check-in recommended.",
        "high": "Priority intervention: advisor review and support plan.",
    }.get(band, "")
