# Algorithms — USAMIS-Python

Three conventional, deterministic, explainable algorithms. They are **not**
artificial intelligence or machine learning. Each is documented, unit-tested,
and kept separate from Flask route handlers.

| # | Algorithm | Module | Unit tests |
|---|---|---|---|
| 1 | Course Enrollment Eligibility | `app/algorithms/enrollment_eligibility.py` | `tests/integration/test_enrollment_algorithm.py`, `tests/integration/test_prerequisites.py` |
| 2 | Academic Performance Calculation | `app/algorithms/academic_performance.py` | `tests/unit/test_academic_performance.py` |
| 3 | Fee Balance and Payment Status | `app/algorithms/fee_balance.py` | `tests/unit/test_fee_balance.py` |

---

## Algorithm 1 — Course Enrollment Eligibility

### Problem definition
Decide whether a student may enroll in a given course offering, without
trusting any client-side claim.

### Business objective
Prevent invalid, duplicate, or over-capacity enrollments while giving the
student a clear, actionable reason when enrollment is not possible.

### Inputs / outputs

Inputs: the student, the offering (with course, semester, capacity), existing
enrollments, prerequisites, and registration state.

Output: an `EligibilityResult` — `eligible` (bool), `reason_code`, human
`message`, optional `reasons` list, and `details` (e.g. enrolled/capacity).

### Preconditions / postconditions
Pre: the caller has an open database session.
Post: no rows are modified; the result fully explains the decision.

### Step-by-step logic
1. Validate the student exists (else `STUDENT_NOT_FOUND`).
2. Validate the student is active (else `STUDENT_NOT_ACTIVE`).
3. Validate the offering exists and is active (else `OFFERING_INACTIVE`).
4. Validate the semester's registration is open (else `REGISTRATION_CLOSED`).
5. Validate the course is active.
6. Reject a duplicate pending/enrolled/completed enrollment (`ALREADY_ENROLLED`).
7. Check each prerequisite for a **published** passing grade ≥ the configured
   minimum (else `PREREQUISITE_NOT_MET`, listing unmet courses).
8. Check capacity: enrolled count < capacity (else `CAPACITY_FULL`).
9. Return `ELIGIBLE` with details.

### Pseudocode
```
function evaluate(student, offering, lock):
    if student is null:            return reject(STUDENT_NOT_FOUND)
    if student.status != active:   return reject(STUDENT_NOT_ACTIVE)
    if offering is null:           return reject(OFFERING_NOT_FOUND)
    if not offering.active:        return reject(OFFERING_INACTIVE)
    if not offering.semester.registration_open: return reject(REGISTRATION_CLOSED)
    if exists active enrollment(student, offering): return reject(ALREADY_ENROLLED)
    for prereq in offering.course.prerequisites:
        best = best_published_grade(student, prereq.required_course)
        if best is null or best < threshold(prereq): return reject(PREREQUISITE_NOT_MET)
    enrolled = count_active_enrollments(offering, lock)
    if enrolled >= offering.capacity: return reject(CAPACITY_FULL)
    return accept(ELIGIBLE)
```

### Flowchart
See `docs/diagrams/04-enrollment-flowchart.mmd` (and `.png`).

### Complexity
Let `n` = number of prerequisites. Each prerequisite issues one indexed
aggregate query; capacity is one indexed count. Overall approximately
O(n) database round trips, O(1) space beyond the result.

### Error cases
Unknown student/offering; inactive student; closed registration; duplicate;
unmet prerequisite; full capacity. All return structured reason codes.

### Example
Student is active, offering open, capacity 40, one prerequisite CS102 with
minimum 60. The student's best published CS102 grade is 55 → result:
`eligible=false`, `reason_code=PREREQUISITE_NOT_MET`, reasons `["CS102 (need >= 60.00)"]`.

### Integration
Called by `app/services/enrollment_service.request_enrollment` and the
`/enrollments/check/<id>` dry-run view.

### Suitability for an MIS
Rule-based eligibility is exactly the kind of deterministic, auditable control
an academic registry requires; every decision is explainable to a student or
administrator.

---

## Algorithm 2 — Academic Performance Calculation

### Problem definition
Compute a credit-weighted academic average from published grades.

### Business objective
Provide a defensible performance summary using documented grading and credit
rules, without inventing an official GPA.

### Inputs / outputs
Inputs: records of `{course_code, credits, score, published}` plus the grading
scale, optional GPA mapping, and pass mark.
Output: `PerformanceResult` — weighted average, graded credits, passed/failed
counts, optional GPA, per-line detail, and notes.

### Preconditions / postconditions
Pre: inputs are plain values (no request context needed).
Post: no side effects; excluded records are explained in `notes`.

### Step-by-step logic
1. For each record: skip unpublished, missing, non-numeric, out-of-range, or
   non-positive-credit entries, noting why.
2. Map each valid score to a letter via the scale.
3. Accumulate `Σ score×credits` and `Σ credits`.
4. Weighted average = `Σ(gᵢcᵢ) / Σ cᵢ`, rounded half-up to 2 dp.
5. If GPA mapping is enabled, compute `Σ(gpᵢcᵢ) / Σ cᵢ`; otherwise GPA is `None`.
6. Count passes (score ≥ pass mark) and failures.

### Pseudocode
```
weighted = 0; credits = 0; points = 0; gpaCredits = 0
for r in records:
    if not r.published or r.score is null: note(excluded); continue
    if r.score < 0 or r.score > 100: note(excluded); continue
    if r.credits <= 0: note(excluded); continue
    weighted += r.score * r.credits; credits += r.credits
    if gpa_enabled: points += grade_point(r.score) * r.credits; gpaCredits += r.credits
average = credits > 0 ? round(weighted / credits, 2) : null
gpa     = (gpa_enabled and gpaCredits > 0) ? round(points / gpaCredits, 2) : null
```

### Formula
Weighted Average = Σ(gᵢcᵢ) / Σcᵢ, where gᵢ is the numeric grade and cᵢ the
course credits.

### Flowchart
See `docs/diagrams/02-system-architecture.mmd` for placement; the arithmetic is
a linear pass and is depicted in the project report's algorithm section.

### Complexity
O(n) time, O(n) space for the returned lines.

### Error cases
No records, zero total credits, invalid grades, missing credits → average is
`None` and a note explains why. No exception is raised for bad data; bad data
is excluded and reported.

### Example
`[(CS101,3,80),(CS102,4,90)]` → weighted average `85.71`, graded credits `7`,
passed `2`.

### Integration
Used by `dashboard` (student dashboard) and `grades.my_grades`.

### Suitability for an MIS
Credit-weighted averaging is the standard, transparent measure; keeping official
GPA behind explicit configuration avoids misrepresenting a numeric average as a
regulated GPA figure.

### Grading policy (documented defaults)

| Score | Letter | Grade point (if GPA enabled) |
|---|---|---|
| 90–100 | A | 4.0 |
| 80–89.99 | B | 3.0 |
| 70–79.99 | C | 2.0 |
| 60–69.99 | D | 1.0 |
| 50–59.99 | E | 0.5 |
| 0–49.99 | F | 0.0 |

Pass mark = 50. GPA conversion is disabled by default (`GPA_ENABLED=false`).

---

## Algorithm 3 — Fee Balance and Payment Status

### Problem definition
Compute a student's outstanding fee balance and payment status.

### Business objective
Provide accurate, decimal-safe fee accounting with explicit treatment of
adjustments and overpayments.

### Inputs / outputs
Inputs: assessments `{amount, adjustment}` and payments `{amount}`.
Output: `FeeResult` — total assessed, adjustments, payable, paid, balance,
credit, status, and notes.

### Preconditions / postconditions
Pre: amounts are decidable as `Decimal`.
Post: negative or zero payments and negative amounts raise `ValueError`
(never silently accepted); overpayment is surfaced as `credit`.

### Step-by-step logic
1. Sum assessments; reject negative amounts.
2. Apply adjustments (≥ 0); if an adjustment exceeds its amount, cap the net at
   zero and note it.
3. Sum payments; reject amounts ≤ 0.
4. Payable = total assessed − adjustments (floored at zero).
5. Balance = payable − paid.
6. Derive status: no charges / outstanding / partially paid / paid / overpaid.

### Formula
Outstanding Balance = Total Fees − Valid Payments − Applicable Adjustments

### Pseudocode
```
assessed = 0; adjustments = 0
for a in assessments:  require a.amount >= 0; assessed += a.amount
                       adj = min(a.adjustment, a.amount); adjustments += adj
paid = 0
for p in payments:     require p.amount > 0; paid += p.amount
payable = max(assessed - adjustments, 0)
balance = payable - paid
if payable == 0 and paid == 0: status = NO_CHARGES
elif balance > 0:  status = paid>0 ? PARTIAL : OUTSTANDING
elif balance == 0: status = PAID
else:              credit = -balance; balance = 0; status = OVERPAID
```

### Status rules

| Condition | Status |
|---|---|
| payable = 0 and paid = 0 | `no_charges` |
| balance > 0 and paid = 0 | `outstanding` |
| balance > 0 and paid > 0 | `partially_paid` |
| balance = 0 and payable > 0 | `paid` |
| paid > payable | `overpaid` (credit recorded) |

### Complexity
O(n + m) time, O(1) space.

### Error cases
Negative assessment, negative/zero payment → `ValueError`. Adjustment larger
than its assessment → capped with a note.

### Example
Assessments `[(1000.00, 0)]`, payments `[(400.00)]` → balance `600.00`,
status `partially_paid`.

### Integration
Used by `fee_service.student_balance`, the student dashboard, and the fee
account view.

### Suitability for an MIS
Decimal arithmetic and explicit status rules give finance staff an auditable,
reproducible figure that cannot drift due to floating-point error or hidden
negative balances.
