# Installation Guide — USAMIS-Python

Complete setup instructions. Windows PowerShell examples are given alongside
general commands.

## 1. Prerequisites

| Requirement | Version used | Notes |
|---|---|---|
| Python | 3.11+ | 3.11.15 verified |
| PostgreSQL | 12+ | 17.10 verified |
| Git | any recent | for cloning |
| pip | bundled with Python | |

Confirm versions:

```powershell
python --version
psql --version            # or: "D:\postgresql\bin\psql.exe" --version
```

## 2. Get the code

```powershell
git clone https://github.com/ISI0007/USAMIS-PROJECT-Python-.git
cd USAMIS-PROJECT-Python-
```

## 3. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

General (Linux/macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` holds runtime dependencies; `requirements-dev.txt` adds the
test and document-generation tools.

## 5. Create the databases

Using the `psql` client:

```powershell
$env:PGPASSWORD='postgres'
& "D:\postgresql\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE usamis_dev;"
& "D:\postgresql\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE usamis_test;"
```

Create a least-privilege application role for production (example):

```sql
CREATE ROLE usamis LOGIN PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE usamis_dev TO usamis;
GRANT USAGE, CREATE ON SCHEMA public TO usamis;
```

## 6. Configure the environment

Copy the template and edit it:

```powershell
Copy-Item .env.example .env
```

Set at least:

```
SECRET_KEY=<long random string>
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_dev
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_test
```

`.env` is git-ignored and must never be committed.

## 7. Apply migrations

```powershell
$env:FLASK_APP='wsgi.py'
$env:FLASK_ENV='development'
python -m flask db upgrade
```

This creates the full schema. To autogenerate a new revision:

```powershell
python -m flask db migrate -m "describe change"
python -m flask db upgrade
```

## 8. Generate demo data (development)

```powershell
python -m flask seed
```

The seed is idempotent — safe to run repeatedly. Use `--reset` to clear demo
tables first (development only).

Demo accounts (development only — change before any shared use):

| Username | Role | Password |
|---|---|---|
| `admin` | Administrator | `Demo_Pass1!` |
| `registrar` | Academic staff | `Demo_Pass1!` |
| `t.mensah` | Teacher | `Demo_Pass1!` |
| `finance` | Finance officer | `Demo_Pass1!` |
| `s.demo` | Student | `Demo_Pass1!` |

Create your own administrator instead:

```powershell
python -m flask create-admin --username admin2 --email a@uni.edu --password 'StrongPass1!'
```

## 9. Run the application

```powershell
python run.py
```

Then open http://127.0.0.1:5000 and sign in.

## 10. Run the tests

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_test'
python -m pytest
```

With coverage:

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

The suite uses the PostgreSQL test database and does not touch development or
production data.

## 11. Production configuration

1. Use a real WSGI server, never the Flask development server:

   ```powershell
   pip install waitress
   waitress-serve --listen=0.0.0.0:8000 wsgi:app
   ```

   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

2. Set environment variables:

   ```
   FLASK_ENV=production
   SECRET_KEY=<strong random value>
   DATABASE_URL=postgresql+psycopg2://usamis:<password>@<host>:5432/usamis_prod
   SESSION_COOKIE_SECURE=true
   ```

3. Terminate TLS at a reverse proxy and serve only over HTTPS.
4. Use a least-privilege database role.
5. Run `flask db upgrade` as part of deployment.
6. Do **not** run the seed command in production.

## 12. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv and install `requirements-dev.txt` |
| `connection refused` to 5432 | PostgreSQL service not running; start it |
| `password authentication failed` | Wrong credentials in `.env` |
| `relation ... does not exist` | Migrations not applied: `flask db upgrade` |
| `CSRF token missing` on a POST | Include the CSRF field (browsers do this automatically) |
| Login returns 429 | Login throttling triggered; wait for the lockout window |
| `psql` not found on PATH | Use the full path, e.g. `D:\postgresql\bin\psql.exe` |
| Alembic `Directory versions does not exist` | Create `migrations/versions/` |
