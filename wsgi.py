"""WSGI entry point for USAMIS-Python.

Exposes ``app`` for WSGI servers (gunicorn/waitress) and for Flask CLI
(``flask --app wsgi``). The development server should only ever be used
locally; production deployments must use a real WSGI server.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":  # pragma: no cover - convenience only
    app.run()
