import io
from app.extensions import db as _db
from app.models import Attendance
from app.services import qr_attendance_service
from tests.integration.test_qr_attendance import _graph
from tests.unit.test_qr_decoder import png


def test_neural_page_requires_authorized_staff(client, login, make_user):
    assert client.get('/predictions/neural').status_code == 302
    make_user(username='risk_student', role='student')
    login('risk_student')
    assert client.get('/predictions/neural').status_code == 403


def test_neural_missing_artifact_and_invalid_prediction(client, login, make_user, app, tmp_path):
    app.config['NEURAL_RISK_ARTIFACT'] = str(tmp_path/'absent.json')
    make_user(username='risk_admin', role='administrator')
    login('risk_admin')
    response = client.get('/predictions/neural')
    assert response.status_code == 200
    assert b'No model has been trained' in response.data
    assert client.post('/predictions/neural', data={}).status_code == 400


def test_four_layer_neural_request(client, login, make_user, app, tmp_path):
    from app.services.neural_risk_service import train_from_csv
    from scripts.generate_risk_demo import generate
    dataset, artifact = tmp_path/'demo.csv', tmp_path/'model.json'
    generate(dataset, count=100)
    train_from_csv(dataset, artifact, data_kind='synthetic', source='Integration-test simulation')
    app.config['NEURAL_RISK_ARTIFACT'] = str(artifact)
    make_user(username='neural_admin', role='administrator')
    login('neural_admin')
    data = dict(prior_average='70', attendance_rate='.85', early_average='65', credit_load='20')
    response = client.post('/predictions/neural', data=data)
    assert response.status_code == 200
    assert b'Model score' in response.data and b'synthetic' in response.data
    data['attendance_rate'] = 'nan'
    assert client.post('/predictions/neural', data=data).status_code == 400


def test_opencv_scan_saves_one_postgres_record(client, login, app, db):
    import pytest
    pytest.importorskip('cv2')
    graph = _graph(db)
    session = qr_attendance_service.open_session(graph['teacher_user'], graph['offering'], secret=app.config['SECRET_KEY'])
    image = png(f'http://localhost/attendance/scan?token={session.token}')
    login('qrstudent')
    for _ in range(2):
        response = client.post('/attendance/scanner', data={'qr_image': (io.BytesIO(image), 'qr.png')}, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
        assert b'Attendance recorded' in response.data
    assert _db.session.scalar(_db.select(_db.func.count(Attendance.id))) == 1


def test_scanner_rejects_tampered_token(client, login, app, db):
    import pytest
    pytest.importorskip('cv2')
    _graph(db)
    login('qrstudent')
    response = client.post('/attendance/scanner', data={'qr_image': (io.BytesIO(png('http://localhost/attendance/scan?token=1:2:3:forged')), 'qr.png')}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert _db.session.scalar(_db.select(_db.func.count(Attendance.id))) == 0
