# USAMIS-Python — Expansion Plan (v1.1 feature set)

**Date:** 2026-10-12
**Status:** Approved by owner — full implementation, external providers behind
adapter interfaces using **offline development stubs** (no API keys, no spend).

This document specifies five additions to USAMIS-Python. Existing behaviour,
routes, models, and tests are preserved; each feature is additive.

---

## Feature set

| ID | Feature | Summary |
|---|---|---|
| F1 | SMS notifications | Fee reminders and critical alerts delivered over an SMS provider abstraction |
| F2 | Online payment gateway | Pay a student's fee balance through a provider abstraction, with a callback/webhook and receipt |
| F3 | QR-code attendance | A teacher shows/prints a per-session QR code; a student scans it to mark their own attendance |
| F4 | AI performance prediction | An explainable model that predicts a student's academic risk from grades and attendance |
| F5 | Parent portal | A parent role linked to one or more students, with read-only progress views |

---

## Design principles

1. **Provider abstraction.** SMS and payment providers sit behind a narrow
   interface (`app/integrations/base.py`) so the app never depends on a vendor.
   Development uses `StubSmsProvider` / `StubPaymentProvider`, which log the
   outbound action and persist the artifact (message row, payment intent row)
   instead of calling the network.
2. **No secrets in code or git.** Real provider credentials, when supplied,
   come from environment variables and are never committed.
3. **Additive migrations.** New tables are added by new Alembic revisions; no
   destructive change to existing tables.
4. **Explainability.** The prediction feature reports *why* it produced a score
   (contributing factors), consistent with the existing three algorithms.
5. **Authorization first.** Every new route is registered in the central
   permission matrix; parent scope is limited to their own linked students.

---

## F1 — SMS notifications

- **Tables:** `sms_message` (recipient, body, status, provider, created_at,
  sent_at, error).
- **Adapter:** `SmsProvider.send(to, body) -> SmsResult`.
- **Triggers:** fee reminder (from the fee-balance algorithm), critical account
  events (e.g. lockout, payment received), and an admin "send reminder" action
  on the fee defaulters report.
- **Reminders:** a management command / scheduled task composes outstanding
  balances into messages for the finance role to review and dispatch.
- **UI:** `/notifications/sms` — list, filter by status, compose and send.

## F2 — Online payment gateway

- **Tables:** `payment_intent` (student, amount, reference, status, provider,
  provider_ref, created_at, completed_at).
- **Adapter:** `PaymentProvider.create_intent(student, amount)` and
  `PaymentProvider.verify(reference)`.
- **Flow:** student/parent opens balance → selects amount → intent created →
  (stub) redirect target returned → callback marks the intent paid and records a
  `payment` row through the existing fee service, so balances update exactly as
  a manual payment would.
- **UI:** "Pay now" on the student fee page; a payments history page for finance
  and for the student.

## F3 — QR-code based attendance

- **Tables:** `attendance_session` (offering, date, token, expires_at, opened_by,
  open flag); `attendance_record` gains an optional `source` column
  (`manual` | `qr`).
- **Flow:** teacher opens a session → a time-limited signed token is rendered as
  a QR code → student scans (mobile page) → token validated → enrolment checked
  → attendance marked `present` with `source='qr'`.
- **Security:** tokens are signed, single-session, time-limited, and validated
  against the student's enrollment in that offering.
- **UI:** `/attendance/offering/<id>/session` for the teacher; `/attendance/scan`
  for the student.

## F4 — AI-based performance prediction

- **Inputs:** published grades (via the academic-performance algorithm) and
  attendance rate (via the attendance module).
- **Model:** an explainable weighted model (transparent coefficients), not a
  black box; the score is a risk band (low / medium / high) with the top
  contributing factors listed. A logistic-style logit is used so the phrasing
  "AI/ML-ready" is honest — the model is a simple, inspectable classifier.
- **Output:** risk band + contributing factors + recommended action.
- **UI:** surfaced on the teacher and administrator dashboards, and on a
  per-student "performance outlook" panel.
- **Tested:** deterministic unit tests over synthetic inputs.

## F5 — Parent portal

- **Tables:** `parent_link` (user_id → student_id, relationship, unique pair).
- **Role:** a `parent` role added to the permission matrix with read-only access
  to linked students' grades, attendance, fees, and enrollment.
- **UI:** parent dashboard listing linked children; each child shows a read-only
  progress summary.
- **Authorization:** every parent route filters by the logged-in parent's links.

---

## Delivery order

F1 → F2 → F3 → F4 → F5, each with model + migration + service + routes + tests,
followed by docs, screenshots, and a single commit per feature. The final commit
updates `PROJECT_STATUS.md`, the SRS scope note, and the presentation.

## Out of scope

- Real provider network calls (stubbed in development; adapters ready for keys).
- Real payment settlement/reconciliation.
- Deep-learning models (the prediction feature is intentionally explainable).
