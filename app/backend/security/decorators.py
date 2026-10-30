"""Server-side authorization decorators.

Authorization must never rely on the UI. Every protected route is wrapped
with one of these decorators (or performs an equivalent ownership check for
student-scoped resources).
"""
from functools import wraps

from flask import abort, current_app
from flask_login import current_user


def login_required(view):
    """Alias of :func:`flask_login.login_required` kept for readable imports."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return view(*args, **kwargs)

    return wrapper


def permission_required(permission: str):
    """Require the current user to hold ``permission``.

    Returns HTTP 403 for authenticated users lacking the permission, and
    401 for anonymous users.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_permission(permission):
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def roles_required(*roles: str):
    """Require the current user's role to be one of ``roles``."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(view):
    """Require the Administrator role."""
    return roles_required("administrator")(view)


def is_safe_redirect(target: str | None) -> bool:
    """Return True when ``target`` is a safe *relative* redirect URL.

    Prevents open-redirect attacks by rejecting absolute URLs, protocol
    relative URLs (``//evil.example``) and anything containing a scheme.
    """
    if not target:
        return False
    if target.startswith("//") or target.startswith("\\"):
        return False
    if "://" in target:
        return False
    if ":" in target.split("/", 1)[0]:
        return False
    return target.startswith("/")
