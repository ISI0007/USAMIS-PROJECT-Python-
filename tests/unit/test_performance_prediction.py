"""Unit tests for Algorithm 4 — Explainable Performance-Risk Prediction.

The model is a published logistic function, so these tests pin the exact
behaviour: monotonicity, band boundaries, explainability (factors/notes) and
sparse-data safety.
"""
from decimal import Decimal

import pytest

from app.algorithms.performance_prediction import (
    ATTENDANCE_BASELINE,
    BAND_HIGH,
    BAND_LOW,
    BAND_MEDIUM,
    GRADE_BASELINE,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    PredictionResult,
    band_label,
    predict_performance,
    recommended_action,
)


def test_returns_prediction_result_with_score_and_band():
    result = predict_performance(weighted_average=65, attendance_rate=0.75)
    assert isinstance(result, PredictionResult)
    assert result.band in (BAND_LOW, BAND_MEDIUM, BAND_HIGH)
    assert Decimal("0.00") <= result.risk_score <= Decimal("1.00")
    assert result.has_data is True


def test_baseline_grade_and_attendance_is_not_high_risk():
    # At the published baselines the two terms are zero, so risk = sigmoid(-0.2)
    # = 0.45, which sits just inside the medium band (>= 0.40).
    result = predict_performance(
        weighted_average=GRADE_BASELINE, attendance_rate=ATTENDANCE_BASELINE / 100.0
    )
    assert result.band == BAND_MEDIUM
    assert result.risk_score == Decimal("0.45")
    assert result.risk_score < Decimal(str(HIGH_RISK_THRESHOLD))


def test_high_grades_and_attendance_is_low_risk():
    result = predict_performance(weighted_average=95, attendance_rate=1.0)
    assert result.band == BAND_LOW
    assert result.risk_score < Decimal("0.10")


def test_low_grades_and_attendance_is_high_risk():
    result = predict_performance(weighted_average=35, attendance_rate=0.10)
    assert result.band == BAND_HIGH
    assert result.risk_score >= Decimal(str(HIGH_RISK_THRESHOLD))


def test_risk_is_monotonic_in_grade():
    """Lower grades must produce a HIGHER risk score."""
    scores = [90, 75, 65, 55, 45, 30]
    risks = [predict_performance(weighted_average=g, attendance_rate=0.75).risk_score
             for g in scores]
    assert risks == sorted(risks)  # ascending as grades fall


def test_risk_is_monotonic_in_attendance():
    rates = [1.0, 0.85, 0.75, 0.6, 0.45, 0.2]
    risks = [predict_performance(weighted_average=65, attendance_rate=r).risk_score
             for r in rates]
    assert risks == sorted(risks)  # ascending as attendance falls


def test_factors_are_explainable_and_sorted_by_impact():
    result = predict_performance(weighted_average=40, attendance_rate=0.5)
    names = {f.name for f in result.factors}
    assert {"Academic average", "Attendance"} <= names
    # Biggest absolute driver first.
    impacts = [abs(f.impact) for f in result.factors]
    assert impacts == sorted(impacts, reverse=True)


def test_grade_driven_case_ranks_grade_first():
    # Grades far below baseline, attendance at baseline => grade is the driver.
    result = predict_performance(weighted_average=30, attendance_rate=ATTENDANCE_BASELINE / 100.0)
    assert result.factors[0].name == "Academic average"


def test_missing_grade_falls_back_and_notes():
    # With no grade the attendance term still contributes: 90% is above the
    # threshold, so a strong attendance record keeps risk low.
    result = predict_performance(weighted_average=None, attendance_rate=0.9)
    assert result.band == BAND_LOW
    assert any("grades" in n.lower() for n in result.notes)
    assert any(f.name == "Academic average" and f.impact == 0.0 for f in result.factors)


def test_missing_attendance_falls_back_and_notes():
    result = predict_performance(weighted_average=70, attendance_rate=None)
    assert any("attendance" in n.lower() for n in result.notes)


def test_no_data_at_all_marks_has_data_false():
    result = predict_performance(weighted_average=None, attendance_rate=None)
    assert result.has_data is False
    assert len(result.notes) == 2
    assert result.risk_score == Decimal("0.45")  # neutral bias, medium band


def test_band_boundaries_are_consistent():
    for grade in range(0, 101, 5):
        for att in (0.0, 0.25, 0.5, 0.75, 1.0):
            r = predict_performance(weighted_average=grade, attendance_rate=att)
            if r.risk_score >= Decimal(str(HIGH_RISK_THRESHOLD)):
                assert r.band == BAND_HIGH
            elif r.risk_score >= Decimal(str(MEDIUM_RISK_THRESHOLD)):
                assert r.band == BAND_MEDIUM
            else:
                assert r.band == BAND_LOW


def test_risk_score_is_quantized_to_two_places():
    result = predict_performance(weighted_average=73, attendance_rate=0.68)
    assert result.risk_score == result.risk_score.quantize(Decimal("0.01"))


def test_band_label_and_action_have_all_bands():
    for band in (BAND_LOW, BAND_MEDIUM, BAND_HIGH):
        assert band_label(band)
        assert recommended_action(band)
    assert "No action" in recommended_action(BAND_LOW)
    assert "Priority" in recommended_action(BAND_HIGH)


def test_unknown_band_labels_fall_back_safely():
    assert band_label("mystery") == "mystery"
    assert recommended_action("mystery") == ""
