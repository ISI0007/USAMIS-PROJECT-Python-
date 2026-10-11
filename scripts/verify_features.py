"""End-to-end feature verification across all roles.

Logs in as each seeded demo account and probes every module route,
asserting expected allow/deny behavior from the RBAC matrix.

Run against a live dev server:
    python scripts/verify_features.py [base_url]
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

# route -> (label, roles allowed to GET it without a 403)
PROBES = [
    ("/dashboard/",                  "Dashboard",           "all"),
    ("/students/",                   "Students list",       {"administrator", "academic_staff", "teacher", "finance"}),
    ("/departments/",                "Departments",         {"administrator", "academic_staff"}),
    ("/programs/",                   "Programs",            {"administrator", "academic_staff"}),
    ("/courses/",                    "Courses",             {"administrator", "academic_staff"}),
    ("/semesters/",                  "Semesters",           {"administrator", "academic_staff"}),
    ("/enrollments/",                "Enrollments",         {"administrator", "academic_staff"}),
    ("/grades/",                     "Grades",              {"administrator", "academic_staff", "teacher"}),
    ("/attendance/",                 "Attendance",          {"administrator", "teacher"}),
    ("/fees/",                       "Fees",                {"administrator", "finance"}),
    ("/reports/",                    "Reports",             {"administrator", "academic_staff", "teacher", "finance"}),
    ("/admin/users",                 "User admin",          {"administrator"}),
    ("/admin/audit",                 "Audit log",           {"administrator"}),
    ("/auth/profile",                "My profile",          "all"),
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    pass


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def fetch(op, url, data=None):
    try:
        req = urllib.request.Request(url, data=data)
        resp = op.open(req)
        return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def login(username):
    op, cj = make_opener()
    _, page = fetch(op, BASE + "/auth/login")
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page)
    tok = m.group(1)
    body = urllib.parse.urlencode(
        {"username": username, "password": PASSWORD, "csrf_token": tok}
    ).encode()
    code, _ = fetch(op, BASE + "/auth/login", body)
    ok = any(c.name == "session" for c in cj)
    return op, ok, code


def main():
    print(f"== USAMIS feature verification against {BASE} ==\n")
    results = []
    for username, role in ACCOUNTS.items():
        op, ok, code = login(username)
        print(f"[{username}] role={role}  login={code}  session={'yes' if ok else 'NO'}")
        if not ok:
            results.append((username, "LOGIN", "FAIL"))
            continue
        for route, label, allowed in PROBES:
            expects = allowed == "all" or role in allowed
            code, _ = fetch(op, BASE + route)
            # 200/302(redirect within app) => allowed; 403 => denied
            got_allowed = code in (200, 302) and code != 403
            status = "OK" if got_allowed == expects else "MISMATCH"
            results.append((username, label, f"{'allow' if got_allowed else 'deny'} (HTTP {code}) {status}"))
        print()

    # summarise
    bad = [r for r in results if r[2].endswith("MISMATCH") or r[2].startswith("FAIL")]
    print("== detail ==")
    for u, l, s in results:
        print(f"  {u:10s} {l:16s} {s}")
    print()
    if bad:
        print(f"RESULT: {len(bad)} mismatch(es) — review above.")
        return 1
    print(f"RESULT: all {len(results)} role/route checks behaved as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
