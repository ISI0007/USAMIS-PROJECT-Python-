# USAMIS four-layer upgrade and demonstration guide

Prepared 30 October 2026. Baseline: GitHub commit `492517e6a32d1ded0f7176460c9283d8afd5035e`.

## Recommendation

Present **QR attendance with OpenCV image decoding and an early academic-risk neural-network experiment**. This is a coherent academic-management demonstration: acquire attendance, store it reliably, then investigate whether earlier academic signals can identify students who need support.

OpenCV QR decoding is computer vision, not deep learning. The trainable 4–32–16–1 neural network provides the deep-learning component. Keep the deterministic enrollment, grade/GPA and fee algorithms because official academic records must follow institutional rules. Compare the neural network with logistic regression rather than assuming the more complicated model wins.

The new risk experiment accepts dated snapshots in CSV. It does **not** silently convert today's cumulative database records into historical training examples. Historical snapshots and later observed outcomes must be collected before claiming a validated institutional predictor. The bundled generator creates labelled synthetic examples for teaching only.

## The four layers

These are logical software layers inside one Flask application, not four separately deployed servers. Layer 3 is called **Academic Processing and Algorithms** throughout the presentation.

| Layer | Responsibility | Code | Independent evidence |
|---|---|---|---|
| 1. Presentation | Render pages, collect input, display results | `app/frontend/templates/`, `app/frontend/static/` | Compile all Jinja templates without a server; inspect rendered pages |
| 2. Application | Route requests, authenticate users, check permissions, adapt form data | Flask blueprint packages, `app/backend/security/`, `app/backend/predictions/neural_views.py` | HTTP, authentication, authorization and invalid-input tests |
| 3. Academic Processing and Algorithms | Apply academic policies, orchestrate workflows, decode QR images, train/infer with models | `app/backend/services/`, `app/algorithms/` | Pure algorithm tests; neural training/serialization; real QR pixel decoding |
| 4. Data | Store and retrieve academic records and model artifacts; enforce constraints | `app/database/models/`, `app/database/repositories/`, `migrations/`, PostgreSQL, `schema.sql` | Repository round-trip, PostgreSQL persistence tests, fresh migrations and schema comparison |

Layer 3 algorithms contain no Flask, SQLAlchemy or PostgreSQL imports. Services coordinate those algorithms with Layer 4. Some original Flask routes still perform simple ORM queries directly; the architecture is a practical logical separation, not a claim that every legacy dependency follows a strict adjacent-layer rule. The new neural route calls the processing service, which calls its repository.

### Request trace: OpenCV attendance

1. Layer 1: a signed-in student takes a photograph or uploads a QR image.
2. Layer 2: the route checks login, the attendance permission and CSRF protection.
3. Layer 3: OpenCV decodes the image. Attendance processing checks the HMAC signature, expiry, open session and course enrollment.
4. Layer 4: PostgreSQL stores the attendance row and audit entry. A repeat scan updates the existing daily attendance record rather than creating a duplicate.
5. Layer 1: the student sees confirmation and their attendance history.

The image is processed in memory. The decoder never follows a URL from an uploaded QR code. An ordinary phone-camera QR link first shows a confirmation page; only POST writes attendance. QR attendance does not prove physical presence and does not prevent a student sharing an active code.

### Request trace: neural experiment

1. Layer 1 displays a research form and held-out results.
2. Layer 2 permits users with `manage_students`, validates the request and handles errors.
3. Layer 3 validates four numerical inputs and performs neural-network inference.
4. Layer 4 loads a versioned JSON artifact, with a PostgreSQL fallback. Offline training reads CSV snapshots and atomically saves the artifact; risk_snapshots and risk_experiments persist the research dataset and trained bundle in SQL.
5. Layer 1 displays a model score, threshold and synthetic-data disclosure where applicable.

No model changes a student's grades, enrollment or official academic standing.

## Layer 3 algorithms

| Algorithm | Purpose | Classification |
|---|---|---|
| Enrollment eligibility | Check status, duplicate enrollment, prerequisites and capacity | Deterministic academic rules |
| Academic performance | Calculate published-grade weighted average and configured GPA | Deterministic calculation |
| Fee balance | Calculate assessments less adjustments and payments using decimals | Deterministic calculation |
| Signed QR validation | Bind a short-lived code to a course session and validate enrollment | Cryptographic validation and academic rules |
| OpenCV QR decoder | Extract the code from uploaded image pixels | Classical computer vision |
| Existing logistic-risk classifier | Learn a present-state rule from current records | Machine learning; existing training-set metrics |
| New logistic baseline | Compare on identical dated snapshots and independent splits | Supervised machine learning |
| New 4–32–16–1 neural network | Estimate a later failure outcome from earlier inputs | Deep learning with two hidden layers |

### Neural-network details

- Inputs: previous average (0–100), attendance proportion (0–1), early assessment average (0–100), credit load (1–40).
- Labels: `failed_later`, from an outcome after `snapshot_date`. The dataset owner must ensure inputs contain only information available at that date.
- Architecture: 4 inputs, 32 ReLU units, 16 ReLU units, one sigmoid output. The comparator uses the same implementation with no hidden layer, which is logistic regression.
- Training: NumPy backpropagation, binary cross-entropy, L2 regularization, fixed seed 42, learning rate 0.03, up to 1,200 epochs, early stopping after 80 epochs without validation improvement. Restore the best validation-loss weights.
- Split: stratified approximately 60/20/20 across distinct students. Exactly one snapshot per student prevents the same student's examples crossing splits. Fit normalization only on training data.
- Selection: validation F1 selects the comparator. The held-out test group is reported afterward and does not select the model.
- Evidence: precision, recall, F1, accuracy, confusion matrix and Brier score. Scores are not established as calibrated real-world probabilities.
- Limitations: the 60-row and 15-per-class minimums are software guards, not guarantees of adequate statistical evidence. Observed data, later-cohort evaluation and institutional policy review remain necessary.

## What already existed, what changed, what remains

**Already present:** Flask, PostgreSQL, six implemented roles including Parent, academic modules, fees, reports, audit logs, QR session links, parent portal, provider adapters and logistic risk code. External provider code does not itself prove a live payment or SMS service is configured.

**Added in this upgrade:** OpenCV image-scanning page; POST confirmation for QR links; independent neural experiment; logistic comparison with held-out evaluation; versioned artifact persistence; synthetic demonstration generator; separate layer checks; reproducible schema export; tracked avatar-column migration; corrected QR-token constraint mapping; four-layer presentation.

**Still required for real-world prediction:** consented/authorized historical snapshots and later outcomes, evaluation on a later cohort, threshold selection appropriate to advisor capacity, calibration checks, and human review of alerts. Synthetic metrics are only a reproducible classroom demonstration.

**Useful next algorithm:** a prerequisite-aware course planner using a directed acyclic graph and topological sorting. It can detect prerequisite cycles and show a valid course order with little training data. Add this only after the current submission is stable.

**Defer:** LSTM until genuine weekly sequences exist; face recognition until there is an actual requirement and suitable validation; Transformers until data scale justifies the complexity. A working, tested QR + MLP demonstration is the recommended scope.

## SQL corrections and installation

The implemented schema contains **22 application tables**. `users.role` stores one role per account; there is no `USER_ROLE` join table in this implementation. `course_offerings` connects course, semester and teacher. Enrollment references an offering, not merely a course.

The `avatar_path` column now has migration `d1a4c6e8f002`. Startup no longer modifies the database. The migration preserves installations where the former startup guard already added the column. QR session-token uniqueness now has the same named constraint in the model and migration.

`schema.sql` is generated directly from SQLAlchemy metadata, including indexes and constraints. It is a fresh-database SQL reference. Normal application installation uses migrations. Do not load this file over an existing database, and do not apply both bootstrap paths to the same database.

From the project directory, after activating a Python 3.11 virtual environment:

```powershell
python -m pip install -r requirements-dev.txt -r requirements-vision.txt
# Configure a development DATABASE_URL and SECRET_KEY in .env.
python -m flask --app wsgi db upgrade
python run.py
```

For independent SQL verification, point `DATABASE_URL` at a fresh disposable PostgreSQL database:

```powershell
python -m flask --app wsgi db upgrade
python scripts/check_schema.py
# [] and exit 0 mean no detected model/migration differences.
python scripts/export_schema.py
```

## Train and demonstrate

```powershell
python scripts/generate_risk_demo.py
python scripts/train_neural_risk.py instance/synthetic-risk.csv --data-kind synthetic --source "Classroom simulation, seed 42"
python run.py
```

Sign in as administrator or registrar and visit `/predictions/neural`. Try earlier average 70, attendance 0.85, early assessment 65 and credit load 20. Explain the model score and compare both models' held-out results. Do not describe synthetic training as training on actual university history.

For QR: a teacher opens `/attendance/offering/<id>/session`; an enrolled student visits `/attendance/scanner` and uploads a photograph of the displayed QR. Demonstrate success, repeat scan, tampered code, and closed/expired session. The regular phone-camera link remains available without OpenCV. For a phone to open the site, it needs a reachable application URL; a laptop's `localhost` URL is not reachable from the phone.

## Independent layer checks

```powershell
# TEST_DATABASE_URL must point to a disposable database: these tests reset tables.
./scripts/verify_layers.ps1 -Python python
python -m pytest -o addopts='' -q --basetemp=instance/test-tmp
```

The layers share one application process and database. Independent verification means testing their responsibilities in isolation, then checking integrated requests; it does not mean every layer is a standalone server.

## Report and PPT corrections

Use the supplied four-layer deck for the teacher's architecture requirement. In the original Word report, replace the three-layer description and simplified SQL with this implementation, change bcrypt to Werkzeug hashing, document the six implemented roles, replace screenshot placeholders, and use the newly recorded test results. Keep the distinction between QR computer vision and neural-network deep learning explicit.

References: Keras structured data examples (https://keras.io/examples/structured_data/); OpenCV QRCodeDetector documentation (https://docs.opencv.org/4.x/de/dc3/classcv_1_1QRCodeDetector.html). Model sizes and project choices above are design decisions for USAMIS, not claims that the cited sources validate this model.

## Completed demo package

See `VERIFICATION_2026_10_30.md` for final evidence. All 194 tests and four independent layer scopes passed. The full SQL export restores all 22 application tables, including 600 synthetic snapshots and the trained model. Ten original illustrated portraits cover all fictional students and teachers. Run `START_PREVIEW.ps1` to restart the local preview.
