"""Debug a single login and print flash messages."""
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

app = create_app("development")
TOKEN_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')

username = sys.argv[1] if len(sys.argv) > 1 else "registrar"

with app.test_client() as c:
    page = c.get("/auth/login")
    match = TOKEN_RE.search(page.get_data(as_text=True))
    tok = match.group(1) if match else ""
    print("token found:", bool(tok))
    r = c.post(
        "/auth/login",
        data={"username": username, "password": "Demo_Pass1!", "csrf_token": tok},
        follow_redirects=True,
    )
    body = r.get_data(as_text=True)
    print("status:", r.status_code)
    for cat, msg in re.findall(r'class="flash flash-(\w+)">([^<]+)<', body):
        print("FLASH", cat, "|", msg.strip())
    if "csrf" in body.lower() and r.status_code == 400:
        print("CSRF error present")
        idx = body.lower().find("csrf")
        print(body[max(0, idx - 200):idx + 200])
