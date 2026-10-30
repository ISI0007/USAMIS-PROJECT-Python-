from app.extensions import db as _db
from app.models import RiskExperiment,RiskSnapshot,Course
from app.repositories.risk_repository import latest_database_bundle
from scripts.generate_risk_demo import generate
from scripts.persist_risk_experiment import persist
from app.services.neural_risk_service import train_from_csv


def test_research_dataset_sql_roundtrip_and_idempotence(db,tmp_path):
    csv,artifact=tmp_path/'data.csv',tmp_path/'model.json'
    generate(csv,100)
    bundle=train_from_csv(csv,artifact,data_kind='synthetic',source='Storage test')
    persist(csv,artifact)
    persist(csv,artifact)
    assert _db.session.scalar(_db.select(_db.func.count(RiskSnapshot.id)))==100
    assert _db.session.scalar(_db.select(_db.func.count(RiskExperiment.id)))==1
    assert latest_database_bundle()['model_version']==bundle['model_version']


def test_course_fractional_credits_roundtrip(db):
    from decimal import Decimal
    course=Course(code='FRACTION',title='Fractional credits',credits=Decimal('1.50'))
    _db.session.add(course);_db.session.commit()
    _db.session.expire_all()
    assert _db.session.get(Course,course.id).credits==Decimal('1.50')
