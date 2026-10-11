"""Academic structure: departments, programs, students, teachers, courses,
prerequisites, semesters and course offerings."""
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .mixins import TimestampMixin


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    programs = relationship(
        "AcademicProgram", back_populates="department", cascade="save-update"
    )
    courses = relationship("Course", back_populates="department")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Department {self.code}>"


class AcademicProgram(TimestampMixin, db.Model):
    __tablename__ = "academic_programs"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_program_dept_code"),
        CheckConstraint("duration_years > 0", name="ck_program_duration_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    total_credits_required: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    department = relationship("Department", back_populates="programs")
    students = relationship("Student", back_populates="program")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AcademicProgram {self.code}>"


class Student(TimestampMixin, db.Model):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("enrollment_status IN ('active','graduated','suspended','withdrawn')",
                        name="ck_student_status_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_number: Mapped[str] = mapped_column(
        String(24), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrollment_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active"
    )

    user = relationship("User", back_populates="student")
    program = relationship("AcademicProgram", back_populates="students")
    department = relationship("Department")
    enrollments = relationship("Enrollment", back_populates="student")
    grades = relationship("Grade", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    fee_assessments = relationship("FeeAssessment", back_populates="student")
    payments = relationship("Payment", back_populates="student")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Student {self.student_number}>"


class Teacher(TimestampMixin, db.Model):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staff_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user = relationship("User", back_populates="teacher")
    department = relationship("Department")
    offerings = relationship("CourseOffering", back_populates="teacher")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Teacher {self.staff_number}>"


class Course(TimestampMixin, db.Model):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("credits > 0 AND credits <= 12", name="ck_course_credits_range"),
        UniqueConstraint("code", name="uq_course_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    department = relationship("Department", back_populates="courses")
    offerings = relationship("CourseOffering", back_populates="course")
    # Self-referential prerequisite graph (course A requires course B).
    prerequisites = relationship(
        "Prerequisite",
        foreign_keys="Prerequisite.course_id",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Course {self.code}>"


class Prerequisite(db.Model):
    """A directed edge: ``course`` requires ``required_course``."""

    __tablename__ = "prerequisites"
    __table_args__ = (
        UniqueConstraint("course_id", "required_course_id", name="uq_prereq_pair"),
        CheckConstraint("course_id <> required_course_id", name="ck_prereq_not_self"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    min_grade: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    course = relationship("Course", foreign_keys=[course_id], back_populates="prerequisites")
    required_course = relationship("Course", foreign_keys=[required_course_id])


class Semester(TimestampMixin, db.Model):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("academic_year", "term", name="uq_semester_year_term"),
        CheckConstraint("term IN ('fall','spring','summer')", name="ck_semester_term_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registration_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    offerings = relationship("CourseOffering", back_populates="semester")

    @property
    def label(self) -> str:
        return f"{self.academic_year} {self.term.title()}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Semester {self.label}>"


class CourseOffering(TimestampMixin, db.Model):
    """A course taught in a specific semester by a specific teacher."""

    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("course_id", "semester_id", name="uq_offering_course_semester"),
        CheckConstraint("capacity > 0", name="ck_offering_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course = relationship("Course", back_populates="offerings")
    semester = relationship("Semester", back_populates="offerings")
    teacher = relationship("Teacher", back_populates="offerings")
    enrollments = relationship("Enrollment", back_populates="offering")

    @property
    def enrolled_count(self) -> int:
        return sum(1 for e in self.enrollments if e.status in ("enrolled", "completed"))

    @property
    def available_seats(self) -> int:
        return max(self.capacity - self.enrolled_count, 0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CourseOffering {self.course_id}@{self.semester_id}>"
