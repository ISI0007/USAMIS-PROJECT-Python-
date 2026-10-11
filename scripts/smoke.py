"""Smoke test: boot the app, log in as each role, hit key pages.

Run: python scripts/smoke.py
Requires a seeded development database.

Uses `limiter.enabled = False` so the deliberate login-throttle does not
interfere with this test harness (throttling itself is covered by the
dedicated security test suite).
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_dev"
)
os.environ.setdefault("SECRET_KEY", "smoke-secret")

from app import create_app  # noqa: E402
from app.extensions import limiter  # noqa: E402

app = create_app("development")
limiter.enabled = False  # test harness only

CREDS = {
    "administrator": "admin",
    "academic_staff": "registrar",
    "teacher": "t.mensah",
    "finance": "finance",
    "student": "s.demo",
}

TOKEN_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')

failures = []


def csrf(client):
    match = TOKEN_RE.search(client.get("/auth/login").get_data(as_text=True))
    return match.group(1) if match else ""


with app.test_client() as client:
    resp = client.get("/dashboard/", follow_redirects=False)
    print(f"anonymous /dashboard/ -> {resp.status_code}")
    if resp.status_code not in (302, 401):
        failures.append("anonymous dashboard not blocked")

for role, username in CREDS.items():
    with app.test_client() as c:
        r = c.post(
            "/auth/login",
            data={"username": username, "password": "Demo_Pass1!", "csrf_token": csrf(c)},
            follow_redirects=True,
        )
        ok = 'action="/auth/logout"' in r.get_data(as_text=True)
        print(f"[{role}] login -> {r.status_code} authenticated={ok}")
        if r.status_code != 200 or not ok:
            failures.append(f"{role} login failed")
            continue
        for path in ("/dashboard/", "/students/", "/courses/", "/semesters/",
                     "/reports/", "/enrollments/", "/fees/", "/admin/users"):
            rr = c.get(path, follow_redirects=True)
            if rr.status_code not in (200, 403):
                failures.append(f"{role} {path} -> {rr.status_code}")
            print(f"  [{role}] {path:16s} {rr.status_code}")

if failures:
    print("\nFAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)

print("\nSMOKE OK")
