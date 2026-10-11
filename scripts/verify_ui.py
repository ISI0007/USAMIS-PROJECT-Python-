"""Deep per-role UI verification.

Beyond HTTP allow/deny, this inspects the *rendered dashboard and sidebar*
of each role and asserts that navigation reflects the RBAC matrix:
no role should see menu links for modules it cannot access.

Run against a live dev server:
    python scripts/verify_ui.py [base_url]
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
PASSWORD = "Demo_Pass1!"

ACCOUNTS = {
    "admin": "administrator",
    "registrar": "academic_staff",
    "t.mensah": "teacher",
    "finance": "finance",
    "s.demo": "student",
}

# Sidebar/nav target hrefs that represent each module, and which roles may see them.
NAV = {
    "/students":     {"administrator", "academic_staff", "teacher", "finance"},
    "/departments":  {"administrator", "academic_staff"},
    "/programs":     {"administrator", "academic_staff"},
    "/courses":      {"administrator", "academic_staff"},
    "/semesters":    {"administrator", "academic_staff"},
    "/enrollments":  {"administrator", "academic_staff"},
    "/grades":       {"administrator", "academic_staff", "teacher"},
    "/attendance":   {"administrator", "teacher"},
    "/fees":         {"administrator", "finance"},
    "/reports":      {"administrator", "academic_staff", "teacher", "finance"},
    "/admin/users":  {"administrator"},
    "/admin/audit":  {"administrator"},
    # Student self-service (visible only to their owners)
    "/enrollments/my": {"student"},
    "/enrollments/request": {"student"},
    "/grades/my":    {"student"},
    "/attendance/my": {"student"},
    "/fees/my":      {"student"},
}


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def fetch(op, url, data=None):
    try:
        resp = op.open(urllib.request.Request(url, data=data))
        return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def login(username):
    op = make_opener()
    _, page = fetch(op, BASE + "/auth/login")
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
    body = urllib.parse.urlencode(
        {"username": username, "password": PASSWORD, "csrf_token": tok}).encode()
    fetch(op, BASE + "/auth/login", body)
    return op


def nav_links(html: str) -> set[str]:
    """Return the set of module hrefs present in the navigation."""
    hrefs = set(re.findall(r'href="([^"]+)"', html))
    found = set()
    for target in NAV:
        # Match /students or /students/ etc, but not /students/5 sub-pages.
        for h in hrefs:
            base = h.rstrip("/")
            if base == target:
                found.add(target)
    return found


def main():
    print(f"== USAMIS per-role UI verification against {BASE} ==\n")
    problems = []
    for username, role in ACCOUNTS.items():
        op = login(username)
        code, dash = fetch(op, BASE + "/dashboard/")
        seen = nav_links(dash)
        print(f"[{username}] role={role}  dashboard HTTP {code}")
        for target, allowed in NAV.items():
            may_see = role in allowed
            does_see = target in seen
            if may_see and not does_see:
                problems.append((username, target, "missing but should be visible"))
                print(f"    ! {target:16s} NOT visible (should be)")
            elif does_see and not may_see:
                problems.append((username, target, "visible but should be hidden"))
                print(f"    ! {target:16s} VISIBLE (should be hidden)")
        print(f"    nav modules visible: {sorted(seen)}")
        print()
    if problems:
        print(f"RESULT: {len(problems)} UI problem(s):")
        for u, t, why in problems:
            print(f"  - {u}: {t} -> {why}")
        return 1
    print("RESULT: navigation matches the RBAC matrix for every role.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
