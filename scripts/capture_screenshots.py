"""Capture real application screenshots of the running USAMIS app.

For each role: open a fresh context, log in once (confirming the POST got a
3xx redirect to a non-login page), then capture the key pages into
docs/screenshots/.

Requires the dev server running and Playwright Chromium installed:

    python -m playwright install chromium
    python scripts/capture_screenshots.py [base_url]

These are genuine captures of the live application -- never mock-ups.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
PASSWORD = "Demo_Pass1!"
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"

CAPTURES = [
    ("admin", [
        ("02-admin-dashboard.png", "/dashboard/", "Administrator dashboard"),
        ("03-students.png", "/students/", "Student management"),
        ("04-courses.png", "/courses/", "Course catalogue"),
        ("05-enrollments.png", "/enrollments/", "Enrollments"),
        ("06-grades.png", "/grades/", "Grade entry"),
        ("07-fees.png", "/fees/", "Fees and payments"),
        ("08-reports.png", "/reports/", "Reports"),
        ("09-admin-users.png", "/admin/users", "User administration"),
        ("10-audit-log.png", "/admin/audit", "Audit log"),
    ]),
    ("t.mensah", [
        ("11-teacher-dashboard.png", "/dashboard/", "Teacher dashboard"),
        ("12-attendance.png", "/attendance/", "Attendance recording"),
    ]),
    ("s.demo", [
        ("13-student-dashboard.png", "/dashboard/", "Student dashboard"),
        ("14-my-grades.png", "/grades/my", "My grades"),
        ("15-my-fees.png", "/fees/my", "My fees"),
        ("16-my-enrollments.png", "/enrollments/my", "My enrollments"),
    ]),
]


def login(page, username: str) -> bool:
    page.goto(BASE + "/auth/login", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", PASSWORD)
    with page.expect_navigation(timeout=15000):
        page.click("button[type=submit]")
    page.wait_for_timeout(600)
    return "/auth/login" not in page.url


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    saved = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Public login page first (no auth).
        anon = browser.new_context(viewport={"width": 1440, "height": 1000})
        ap = anon.new_page()
        ap.goto(BASE + "/auth/login", wait_until="domcontentloaded")
        ap.wait_for_timeout(500)
        ap.screenshot(path=str(OUT / "01-login.png"), full_page=True)
        anon.close()
        saved += 1
        print("  saved 01-login.png  <-  /auth/login  (Login page)")

        for username, pages in CAPTURES:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            if not login(page, username):
                print(f"  !! could not log in as {username}; skipping")
                ctx.close()
                continue
            print(f"  [{username}] logged in -> {page.url}")
            for filename, path, label in pages:
                page.goto(BASE + path, wait_until="domcontentloaded")
                page.wait_for_timeout(400)
                if "/auth/login" in page.url:
                    print(f"  !! {path} bounced to login; skipping {filename}")
                    continue
                page.screenshot(path=str(OUT / filename), full_page=True)
                saved += 1
                print(f"  saved {filename}  <-  {path}  ({label})")
            ctx.close()
        browser.close()

    print(f"\nCaptured {saved} screenshots into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
