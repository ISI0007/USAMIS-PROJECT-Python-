# USAMIS verification recorded 30 October 2026

The upgrade runs locally at http://127.0.0.1:5055. It is a classroom demonstration with fictional people and synthetic training data.

## Verified results

- Full PostgreSQL-backed suite: **194 passed**, zero failures or skips; 68.01 seconds. Evidence: `instance/verification.xml`.
- Independent layer checks: all four scopes in `scripts/verify_layers.ps1` passed. Layers are logical responsibilities inside one application, not four servers.
- Browser verification: 24 pages plus one neural form submission returned HTTP 200, across administrator, teacher, student and parent accounts, with no captured JavaScript page errors.
- OpenCV integration tests decode actual QR pixels, persist attendance, reject tampered codes and keep repeat scans idempotent. A physical-phone classroom trial remains to be done.
- Final demo migration metadata comparison: `[]`. Alembic does not comprehensively compare CHECK constraints; separate persistence tests and the fractional-credit migration cover the discovered credit constraint mismatch.
- Complete SQL dump restored successfully into a separate empty PostgreSQL database. Every table count matches the source.
- All eight student profiles and both teacher profiles have local fictional illustrated portraits. These are display assets, not neural-network training data.

## Demo database

22 application tables, plus Alembic version tracking. 14 users, 8 students, 2 teachers, 3 departments, 1 program, 8 semesters, 44 courses, 44 offerings, 231 enrollments, 217 grades, 868 attendance rows, 24 fee assessments, 6 payments, 7 prerequisites, 2 parent links, 8 queued demo SMS records, 1 stub payment intent, 600 research snapshots and 1 trained experiment. Audit and attendance-session counts may increase during use.

SQL stores the avatar paths; the accompanying application folder contains the ten PNG files. External SMS and payment providers were not exercised. The pending demo payment and queued messages are intentionally labelled stub/demo.

## Neural experiment

Dataset SHA/version is recorded in the JSON artifact and SQL research tables. Fixed seed 42; 359 training, 120 validation, 121 test students. Neural architecture: four inputs, 32 and 16 ReLU hidden units, sigmoid output. Train-only standardization and validation-based early stopping.

| Model | Validation F1 | Test precision | Test recall | Test F1 |
|---|---:|---:|---:|---:|
| Logistic regression | 0.772 | 0.725 | 0.806 | 0.763 |
| Neural network | 0.750 | 0.754 | 0.839 | 0.794 |

Validation F1 selects logistic regression. The form explicitly demonstrates the neural network for comparison. Synthetic results establish that training and inference run; they do not establish real-student accuracy or calibrated probability.

## Remaining submission preparation

Use the updated presentation and report supplement to replace stale architecture, simplified ER/SQL and old test claims in the original investigation report. Rehearse on the classroom equipment. Real historical snapshots and observed future outcomes are needed before deployment as an academic support predictor. Production deployment also needs persistent rate-limit storage and environment-specific configuration.
