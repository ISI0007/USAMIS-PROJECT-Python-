"""Layer 3: decode a QR image locally with OpenCV; never follow its URL."""
import io
from urllib.parse import parse_qs, urlsplit

MAX_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 12_000_000


def decode_attendance_image(content):
    if not content or len(content) > MAX_BYTES:
        raise ValueError("Choose a QR image smaller than 4 MB.")
    try:
        import cv2
        import numpy as np
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise ValueError("Image scanning is unavailable. Install requirements-vision.txt or scan the QR with your phone camera.") from exc
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Choose an image smaller than 12 megapixels.")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The upload is not a supported image.") from exc
    matrix = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if matrix is None:
        raise ValueError("The image could not be read.")
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(matrix)
    if not decoded:
        raise ValueError("No readable QR code found. Try a clearer image.")
    parsed = urlsplit(decoded)
    if parsed.scheme not in {"http", "https"} or parsed.path != "/attendance/scan":
        raise ValueError("This QR code is not an attendance code.")
    tokens = parse_qs(parsed.query).get("token", [])
    if len(tokens) != 1 or len(tokens[0]) > 128:
        raise ValueError("This QR code has no valid attendance token.")
    # Host is deliberately never opened. Layer 3 verifies the local HMAC/session.
    return tokens[0]
