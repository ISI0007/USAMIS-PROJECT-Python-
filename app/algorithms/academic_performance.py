"""Algorithm 2 — Academic Performance Calculation.

Credit-weighted numeric average over *published* grades, with an optional,
explicitly-configured grade-point mapping. A weighted numeric average is NOT
an official GPA unless the institution's policy defines the conversion; the
GPA field is therefore ``None`` unless ``GPA_ENABLED`` is set.

See ``docs/ALGORITHMS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

# Documented default letter-grade scale (0-100). Configurable via config;
# documented in docs/ALGORITHMS.md.
DEFAULT_SCALE: list[tuple[float, float, str, float | None]] = [
    (90.0, 100.0, "A", 4.0),
    (80.0, 90.0, "B", 3.0),
    (70.0, 80.0, "C", 2.0),
    (60.0, 70.0, "D", 1.0),
    (50.0, 60.0, "E", 0.5),
    (0.0, 50.0, "F", 0.0),
]

PASS_MARK = Decimal("50.00")


@dataclass
class GradeLine:
    course_code: str
    credits: int
    score: Decimal
    letter: str
    grade_point: float | None


@dataclass
class PerformanceResult:
    weighted_average: Decimal | None
    total_credits: int
    graded_credits: int
    gpa: float | None
    passed: int
    failed: int
    lines: list[GradeLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def letter_for(score: Decimal | float, scale=None) -> str:
    """Map a numeric score to a letter grade using the configured scale."""
    value = float(score)
    for low, high, letter, _gp in (scale or DEFAULT_SCALE):
        if low <= value < high or (value == 100.0 and high == 100.0):
            return letter
    return "F"


def grade_point_for(score: Decimal | float, scale=None, enabled: bool = False):
    """Return the grade point for a score only when GPA mapping is enabled."""
    if not enabled:
        return None
    value = float(score)
    for low, high, _letter, gp in (scale or DEFAULT_SCALE):
        if low <= value < high or (value == 100.0 and high == 100.0):
            return gp
    return 0.0


def _q(value: Decimal) -> Decimal:
    """Round a Decimal to 2 places, half-up, for display."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_performance(
    records: list[dict],
    *,
    gpa_enabled: bool = False,
    scale=None,
    pass_mark: Decimal = PASS_MARK,
) -> PerformanceResult:
    """Compute the credit-weighted academic performance.

    :param records: iterable of dicts with keys ``course_code`` (str),
        ``credits`` (int > 0), ``score`` (Decimal|float|None) and
        ``published`` (bool). Unpublished or score-less records are excluded
        from the weighted average but reported in ``notes``.

    Edge cases handled explicitly: empty input, zero total credits, invalid
    (negative / >100 / non-numeric) grades and missing credits.
    """
    lines: list[GradeLine] = []
    notes: list[str] = []
    weighted_sum = Decimal("0")
    graded_credits = 0
    passed = 0
    failed = 0
    gpa_points = Decimal("0")
    gpa_credits = 0

    for rec in records:
        code = str(rec.get("course_code", "?"))
        published = rec.get("published", True)

        if not published:
            notes.append(f"{code}: unpublished grade excluded from average.")
            continue

        raw_score = rec.get("score")
        if raw_score is None:
            notes.append(f"{code}: no grade recorded; excluded.")
            continue

        try:
            score = Decimal(str(raw_score))
        except Exception:
            notes.append(f"{code}: non-numeric grade '{raw_score}' excluded.")
            continue

        if score < 0 or score > 100:
            notes.append(f"{code}: grade {score} out of range 0-100; excluded.")
            continue

        credits = rec.get("credits")
        try:
            credits = int(credits)
        except (TypeError, ValueError):
            notes.append(f"{code}: invalid credits; excluded.")
            continue
        if credits <= 0:
            notes.append(f"{code}: non-positive credits; excluded.")
            continue

        letter = letter_for(score, scale)
        gp = grade_point_for(score, scale, enabled=gpa_enabled)
        lines.append(
            GradeLine(course_code=code, credits=credits, score=_q(score),
                      letter=letter, grade_point=gp)
        )

        weighted_sum += score * credits
        graded_credits += credits
        if score >= pass_mark:
            passed += 1
        else:
            failed += 1

        if gpa_enabled and gp is not None:
            gpa_points += Decimal(str(gp)) * credits
            gpa_credits += credits

    weighted_average = (
        _q(weighted_sum / graded_credits) if graded_credits > 0 else None
    )
    if graded_credits == 0:
        notes.append("No eligible published grades; weighted average is undefined.")

    gpa = float(_q(gpa_points / gpa_credits)) if (gpa_enabled and gpa_credits > 0) else None

    return PerformanceResult(
        weighted_average=weighted_average,
        total_credits=graded_credits,
        graded_credits=graded_credits,
        gpa=gpa,
        passed=passed,
        failed=failed,
        lines=lines,
        notes=notes,
    )
