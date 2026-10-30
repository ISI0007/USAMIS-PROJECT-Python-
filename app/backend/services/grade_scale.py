"""Grade scale used by the Grade Management UI (0-100 -> letter -> GPA points).

This is the *interactive* scale shown in the Grade Management page and the
"Enter Grade" modal. It matches the letter grades displayed in the records
table (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, F) with 4.0-scale grade points.

The stored ``Grade.letter`` is written from this same scale so the record table,
the auto-computed fields in the modal and the stored value always agree.
"""
from __future__ import annotations

from decimal import Decimal

# (low inclusive, high exclusive, letter, grade points)
GRADE_SCALE: list[tuple[float, float, str, float]] = [
    (90.0, 101.0, "A+", 4.0),
    (85.0, 90.0, "A", 4.0),
    (80.0, 85.0, "A-", 3.7),
    (77.0, 80.0, "B+", 3.3),
    (73.0, 77.0, "B", 3.0),
    (70.0, 73.0, "B-", 2.7),
    (67.0, 70.0, "C+", 2.3),
    (63.0, 67.0, "C", 2.0),
    (60.0, 63.0, "C-", 1.7),
    (57.0, 60.0, "D+", 1.3),
    (50.0, 57.0, "D", 1.0),
    (0.0, 50.0, "F", 0.0),
]

_PASS_LETTERS = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D"}


def letter_for_score(score) -> str:
    """Map a numeric score to a letter grade, or '' when out of range."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return ""
    if value < 0 or value > 100:
        return ""
    for low, high, letter, _gp in GRADE_SCALE:
        if low <= value < high:
            return letter
    return "F"


def points_for_score(score):
    """Grade points for a score, or None when the score is invalid."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 100:
        return None
    for low, high, _letter, gp in GRADE_SCALE:
        if low <= value < high:
            return gp
    return 0.0


def points_for_letter(letter) -> float | None:
    for _low, _high, lt, gp in GRADE_SCALE:
        if lt == letter:
            return gp
    return None


def is_pass(letter) -> bool:
    return letter in _PASS_LETTERS


def scale_as_json() -> list[dict]:
    return [{"low": low, "high": high, "letter": letter, "points": gp}
            for low, high, letter, gp in GRADE_SCALE]
