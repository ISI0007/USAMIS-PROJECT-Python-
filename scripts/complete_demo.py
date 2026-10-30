"""Complete the isolated fictional demonstration; no external messages sent."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from app.models import Student,Teacher,User,SmsMessage,PaymentIntent,CourseOffering,AttendanceSession
from app.seed import DEMO_PASSWORD
from app.services.qr_attendance_service import open_session

if __name__=='__main__':
    app=create_app()
    with app.app_context():
        if 'codex_demo' not in str(db.engine.url.database):
            raise SystemExit('This helper is restricted to the isolated codex_demo database.')
        students=db.session.scalars(db.select(Student).order_by(Student.student_number)).all()
        for i,s in enumerate(students,1):
            if s.user is None:
                u=User(username=f's.demo{i}',email=s.email,full_name=s.full_name,role='student',status='active',is_active_flag=True)
                u.set_password(DEMO_PASSWORD)
                db.session.add(u);db.session.flush();s.user_id=u.id
            else:
                u=s.user
            u.avatar_path=f'images/demo-avatars/student-{i}.png'
        teachers=db.session.scalars(db.select(Teacher).order_by(Teacher.staff_number)).all()
        for i,t in enumerate(teachers,1):
            t.user.avatar_path=f'images/demo-avatars/teacher-{i}.png'
        admin=db.session.scalar(db.select(User).where(User.username=='admin'))
        for s in students:
            if not db.session.scalar(db.select(SmsMessage.id).where(SmsMessage.student_id==s.id)):
                db.session.add(SmsMessage(recipient=s.phone,body='DEMO ONLY: review your academic portal for this term.',category='general',status='queued',provider='demo-not-sent',student_id=s.id,created_by_id=admin.id))
        if not db.session.scalar(db.select(PaymentIntent.id)):
            db.session.add(PaymentIntent(student_id=students[0].id,amount=100,currency='USD',reference='DEMO-PENDING-001',status='pending',provider='stub',created_by_id=admin.id))
        db.session.commit()
        offering=db.session.scalar(db.select(CourseOffering).order_by(CourseOffering.id))
        session=open_session(admin,offering,ttl_minutes=240,secret=app.config['SECRET_KEY'])
        print(f'Completed {len(students)} student and {len(teachers)} teacher profiles. QR offering: {offering.id}. Session: {session.id}')
