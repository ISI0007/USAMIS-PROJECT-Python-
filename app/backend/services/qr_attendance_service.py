"""QR-code attendance business rules (F3).

A teacher opens a session for a course offering. The session carries a signed,
time-limited token rendered as a QR code. A student scans it; if the token is
valid and the student is enrolled, their attendance is marked ``present`` with
``source='qr'``.

Tokens are signed with the app secret key so they cannot be forged, and are
bound to a single session (no reuse across offerings/dates).
"""
from __future__ import annotations

import datetime as dt
import hmac
import hashlib

from ..extensions import db
from ..models import Attendance, AttendanceSession, CourseOffering, Enrollment, Student
from ..models.mixins import utcnow
from . import audit

DEFAULT_TTL_MINUTES = 15


class QRAttendanceError(ValueError):
    """Raised for invalid QR attendance operations."""


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"),
                    hashlib.sha256).hexdigest()[:32]


def generate_token(session_id: int, offering_id: int, expires_at, secret: str) -> str:
    """Build a signed token binding (session, offering, expiry)."""
    exp = int(expires_at.timestamp())
    payload = f"{session_id}:{offering_id}:{exp}"
    return f"{payload}:{_sign(payload, secret)}"


def verify_token(token: str, secret: str) -> tuple[int, int, int] | None:
    """Return (session_id, offering_id, exp) if the signature is valid, else None."""
    parts = (token or "").split(":")
    if len(parts) != 4:
        return None
    sid, oid, exp, sig = parts
    if not (sid.isdigit() and oid.isdigit() and exp.lstrip("-").isdigit()):
        return None
    payload = f"{sid}:{oid}:{exp}"
    expected = _sign(payload, secret)
    if not hmac.compare_digest(expected, sig):
        return None
    return int(sid), int(oid), int(exp)


def open_session(actor, offering: CourseOffering, *, ttl_minutes: int = DEFAULT_TTL_MINUTES,
                 secret: str) -> AttendanceSession:
    """Create an open, time-limited QR attendance session."""
    if ttl_minutes <= 0 or ttl_minutes > 240:
        raise QRAttendanceError("Session TTL must be between 1 and 240 minutes.")

    # Close any other open sessions for this offering (one live QR at a time).
    for other in db.session.execute(
        db.select(AttendanceSession).where(
            AttendanceSession.offering_id == offering.id,
            AttendanceSession.is_open.is_(True))
    ).scalars().all():
        other.is_open = False

    now = utcnow()
    expires = now + dt.timedelta(minutes=ttl_minutes)
    session = AttendanceSession(
        offering_id=offering.id,
        session_date=now,
        expires_at=expires,
        is_open=True,
        opened_by_id=actor.id if actor else None,
        token="pending",  # replaced below (needs the id)
    )
    db.session.add(session)
    db.session.flush()
    session.token = generate_token(session.id, offering.id, expires, secret)

    audit.log_action("attendance_session_opened", "AttendanceSession", session.id,
                     summary=f"offering {offering.id}, TTL {ttl_minutes}m")
    db.session.commit()
    return session


def close_session(actor, session: AttendanceSession) -> AttendanceSession:
    session.is_open = False
    audit.log_action("attendance_session_closed", "AttendanceSession", session.id,
                     summary=f"offering {session.offering_id}")
    db.session.commit()
    return session


def scan(actor, token: str, *, secret: str, today: dt.date | None = None) -> Attendance:
    """Mark the scanning student present for the session the token identifies."""
    today = today or dt.date.today()

    verified = verify_token(token, secret)
    if verified is None:
        raise QRAttendanceError("This QR code is invalid.")
    session_id, offering_id, exp = verified

    session = db.session.get(AttendanceSession, session_id)
    if session is None or session.offering_id != offering_id:
        raise QRAttendanceError("This attendance session no longer exists.")
    if not session.is_active():
        raise QRAttendanceError("This attendance session has closed or expired.")
    if dt.datetime.utcfromtimestamp(exp) < dt.datetime.utcnow():
        raise QRAttendanceError("This QR code has expired.")

    student = db.session.execute(
        db.select(Student).where(Student.user_id == actor.id)
    ).scalars().first()
    if student is None:
        raise QRAttendanceError("Your account is not linked to a student profile.")

    enrolled = db.session.execute(
        db.select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.offering_id == offering_id,
            Enrollment.status.in_(("enrolled", "completed")))
    ).scalars().first()
    if enrolled is None:
        raise QRAttendanceError("You are not enrolled in this course.")

    existing = db.session.execute(
        db.select(Attendance).where(
            Attendance.student_id == student.id,
            Attendance.offering_id == offering_id,
            Attendance.session_date == today)
    ).scalars().first()
    if existing is not None:
        existing.status = "present"
        existing.source = "qr"
        existing.session_id = session.id
        existing.recorded_by_id = actor.id
        record = existing
    else:
        record = Attendance(
            student_id=student.id, offering_id=offering_id,
            session_date=today, status="present", source="qr",
            session_id=session.id, recorded_by_id=actor.id)
        db.session.add(record)

    audit.log_action("attendance_qr_scanned", "Attendance", None,
                     summary=f"student {student.student_number} offering {offering_id}")
    db.session.commit()
    return record
