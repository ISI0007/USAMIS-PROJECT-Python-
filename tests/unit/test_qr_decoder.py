import io
import pytest
import qrcode
from app.algorithms.qr_decoder import decode_attendance_image


def png(text):
    stream = io.BytesIO()
    qrcode.make(text).save(stream, format='PNG')
    return stream.getvalue()


def test_decodes_actual_qr_pixels():
    pytest.importorskip('cv2')
    assert decode_attendance_image(png('http://localhost:5000/attendance/scan?token=1:2:3:abc')) == '1:2:3:abc'


@pytest.mark.parametrize('content', [b'', b'not an image', b'x' * (4*1024*1024+1)], ids=['empty','not-image','oversized'])
def test_rejects_bad_uploads(content):
    with pytest.raises(ValueError):
        decode_attendance_image(content)


def test_does_not_open_arbitrary_qr_links():
    pytest.importorskip('cv2')
    with pytest.raises(ValueError, match='attendance'):
        decode_attendance_image(png('https://example.com/'))
