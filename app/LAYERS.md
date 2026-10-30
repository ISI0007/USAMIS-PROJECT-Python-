# Four application layers

1. **frontend/**: HTML templates, CSS, JavaScript and illustrated profile images.
2. **backend/**: Flask routes, forms, authentication, authorization, workflow services and application configuration.
3. **algorithms/**: standalone academic calculations, QR image decoding and neural-network implementation.
4. **database/**: SQLAlchemy models and data repositories. PostgreSQL migrations are in the project-level `migrations/` folder and the generated schema is `schema.sql`.

`app/__init__.py` connects these folders into one Flask application. It extends the package search path for backend and database so existing imports and integrations remain compatible. The layers are logical components of one application, not four separately running servers. Unit tests exercise algorithms independently; web and database workflows also have integration tests. Some legacy routes access database models directly.
