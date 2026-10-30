"""Profile-photo (avatar) handling.

Photos are stored under ``app/frontend/static/uploads/avatars`` with a per-user
filename, and the relative path is recorded on ``User.avatar_path``. Only
common raster formats are accepted, the file is size-limited and the stored
extension is derived from the validated content type so a client cannot pick
an executable extension.
"""
from __future__ import annotations

import os

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
# 2 MB
MAX_BYTES = 2 * 1024 * 1024


class AvatarError(ValueError):
    """Raised when an uploaded avatar is missing or invalid."""


def _avatar_dir() -> str:
    path = os.path.join(current_app.static_folder, "uploads", "avatars")
    os.makedirs(path, exist_ok=True)
    return path


def save_avatar(user, file_storage) -> str:
    """Validate and store an uploaded avatar; return the relative path.

    The relative path is suitable for ``url_for('static', filename=...)``.
    """
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise AvatarError("Choose an image file to upload.")

    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        raise AvatarError("That file has no extension.")
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AvatarError("Use a PNG, JPG, GIF or WEBP image.")

    # Size check without loading the whole file into memory twice.
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_BYTES:
        raise AvatarError("Image is larger than 2 MB.")

    target_name = f"user_{user.id}.{ext}"
    full_path = os.path.join(_avatar_dir(), target_name)
    file_storage.stream.seek(0)
    file_storage.save(full_path)

    rel = f"uploads/avatars/{target_name}"
    user.avatar_path = rel
    return rel


def remove_avatar(user) -> None:
    """Delete the stored avatar file (if any) and clear the path."""
    if not user.avatar_path:
        return
    full = os.path.join(_avatar_dir(), os.path.basename(user.avatar_path))
    try:
        if os.path.exists(full):
            os.remove(full)
    except OSError:  # pragma: no cover
        current_app.logger.warning("Could not remove avatar %s", full)
    user.avatar_path = None
