"""Unit tests for Algorithm 2 — Academic Performance Calculation."""
from decimal import Decimal

import pytest

from app.algorithms.academic_performance import (
    calculate_performance,
    letter_for,
)


def test_weighted_average_basic():
    records = [
        {"course_code": "CS101", "credits": 3, "score": 80, "published": True},
        {"course_code": "CS102", "credits": 4, "score": 90, "published": True},
    ]
    result = calculate_performance(records)
    # (80*3 + 90*4) / 7 = (240 + 360) / 7 = 85.71
    assert result.weighted_average == Decimal("85.71")
    assert result.graded_credits == 7
    assert result.passed == 2
    assert result.failed == 0


def test_unpublished_grades_excluded():
    records = [
        {"course_code": "CS101", "credits": 3, "score": 80, "published": True},
        {"course_code": "CS102", "credits": 4, "score": 100, "published": False},
    ]
    result = calculate_performance(records)
    assert result.weighted_average == Decimal("80.00")
    assert result.graded_credits == 3
    assert any("unpublished" in n.lower() for n in result.notes)


def test_missing_score_excluded():
    records = [{"course_code": "CS101", "credits": 3, "score": None, "published": True}]
    result = calculate_performance(records)
    assert result.weighted_average is None
    assert result.graded_credits == 0


def test_zero_credits_returns_none():
    result = calculate_performance([])
    assert result.weighted_average is None
    assert result.graded_credits == 0


def test_out_of_range_grades_excluded():
    records = [
        {"course_code": "A", "credits": 3, "score": -5, "published": True},
        {"course_code": "B", "credits": 3, "score": 150, "published": True},
    ]
    result = calculate_performance(records)
    assert result.weighted_average is None
    # Two out-of-range notes plus the "no eligible grades" summary note.
    assert sum(1 for n in result.notes if "out of range" in n) == 2


def test_non_numeric_score_excluded():
    records = [{"course_code": "A", "credits": 3, "score": "abc", "published": True}]
    result = calculate_performance(records)
    assert result.weighted_average is None


def test_non_positive_credits_excluded():
    records = [{"course_code": "A", "credits": 0, "score": 80, "published": True}]
    result = calculate_performance(records)
    assert result.weighted_average is None


def test_pass_fail_counts_use_pass_mark():
    records = [
        {"course_code": "A", "credits": 3, "score": 49, "published": True},
        {"course_code": "B", "credits": 3, "score": 50, "published": True},
    ]
    result = calculate_performance(records)
    assert result.passed == 1
    assert result.failed == 1


def test_gpa_none_when_disabled():
    records = [{"course_code": "A", "credits": 3, "score": 95, "published": True}]
    result = calculate_performance(records, gpa_enabled=False)
    assert result.gpa is None


def test_gpa_computed_when_enabled():
    records = [
        {"course_code": "A", "credits": 3, "score": 95, "published": True},  # A -> 4.0
        {"course_code": "B", "credits": 3, "score": 85, "published": True},  # B -> 3.0
    ]
    result = calculate_performance(records, gpa_enabled=True)
    assert result.gpa == pytest.approx(3.5)


def test_letter_boundaries():
    assert letter_for(90) == "A"
    assert letter_for(89.99) == "B"
    assert letter_for(50) == "E"
    assert letter_for(49.99) == "F"
    assert letter_for(100) == "A"
    assert letter_for(0) == "F"


def test_rounding_half_up():
    records = [
        {"course_code": "A", "credits": 3, "score": 85.005, "published": True},
    ]
    result = calculate_performance(records)
    assert result.weighted_average == Decimal("85.01")
