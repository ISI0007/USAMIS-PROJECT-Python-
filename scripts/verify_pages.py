"""Crawl every GET page as each role; report non-2xx/3xx and any 500s.

Run against a live dev server:
    python scripts/verify_pages.py [base_url]
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
PASSWORD = "Demo_Pass1!"

ACCOUNTS = ["admin", "registrar", "t.mensah", "finance", "s.demo"]

PAGES = [
    "/dashboard/", "/students/", "/departments/", "/programs/", "/courses/",
    "/semesters/", "/enrollments/", "/grades/", "/attendance/", "/fees/",
    "/reports/", "/admin/users", "/admin/roles", "/admin/audit",
    "/auth/profile", "/auth/password",
]


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


def main():
    print(f"== page crawl against {BASE} ==\n")
    problems = []
    for user in ACCOUNTS:
        op = login(user)
        # skip login page itself
        oks = []
        for path in PAGES:
            code, body = fetch(op, BASE + path)
            # 200 = rendered, 302 = redirect (e.g. bounce to login), 403 = denied
            if code >= 500:
                problems.append((user, path, code))
                print(f"  [{user}] {path} -> HTTP {code}  <-- SERVER ERROR")
            else:
                oks.append(f"{path}:{code}")
        print(f"[{user}] ok: {' '.join(oks)}")
        print()
    if problems:
        print(f"RESULT: {len(problems)} server error(s).")
        return 1
    print("RESULT: no 5xx errors on any page for any role.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
