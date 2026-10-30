"""Compare a disposable migrated PostgreSQL database with application models.

Requires DATABASE_URL pointing to a dedicated test database. Never resets it.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app import create_app
from app.extensions import db

if __name__ == '__main__':
    app = create_app()
    with app.app_context(), db.engine.connect() as connection:
        changes = compare_metadata(MigrationContext.configure(connection, opts={'compare_type': True}), db.metadata)
        print(json.dumps(changes, default=str, indent=2))
        sys.exit(bool(changes))
