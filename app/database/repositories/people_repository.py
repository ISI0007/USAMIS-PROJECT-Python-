"""Layer 4 directory queries."""
from sqlalchemy.orm import joinedload
from ..extensions import db
from ..models import Student, Teacher


def directory_records():
    students=db.session.scalars(db.select(Student).options(joinedload(Student.user),joinedload(Student.program)).order_by(Student.student_number)).all()
    teachers=db.session.scalars(db.select(Teacher).options(joinedload(Teacher.user),joinedload(Teacher.department)).order_by(Teacher.staff_number)).all()
    return students,teachers
