"""Development runner for USAMIS-Python.

Usage:
    python run.py

Loads configuration from ``.env`` and starts the Flask development server.
This entry point intentionally refuses to be used as a production server.
"""
import os

from app import create_app

app = create_app()


if __name__ == "__main__":  # pragma: no cover - convenience only
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host=host, port=port, debug=debug)
