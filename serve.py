"""Stable demo/dev server entry point for USAMIS-Python.

Always starts a SINGLE Flask process with the reloader and debug mode off.
This avoids the multi-process reloader chain that splits sessions across
processes and causes spurious CSRF ("session token is missing") errors when
browsing the app.

Usage:
    python serve.py                 # http://127.0.0.1:5000
    FLASK_RUN_PORT=8080 python serve.py

Config comes from .env (SECRET_KEY must stay stable across restarts so that
existing session cookies remain valid).
"""
import os

from app import create_app


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "development")
    app = create_app()
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    print(f"USAMIS running at http://{host}:{port}  (single process, no reloader)")
    # debug=False + use_reloader=False => exactly one process, stable SECRET_KEY.
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
