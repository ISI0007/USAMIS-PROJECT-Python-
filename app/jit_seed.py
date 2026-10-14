"""Apply JIT real departments + majors to the seed.

Adds the real JIT departments/schools on top of the existing three, and creates
an academic programme per department so the "departments & programmes" pages are
populated with the institution's real structure.

Idempotent: safe to re-run (upserts on natural keys).
"""
from __future__ import annotations

from .extensions import db
from .jit_data import JIT_DEPARTMENTS
from .models import AcademicProgram, Department
from .seed import _get_or_create


def seed_jit_departments() -> None:
    # Existing core departments keep their current identity; we add the rest.
    for code, name, description, majors in JIT_DEPARTMENTS:
        dept, _ = _get_or_create(
            Department,
            {"name": name, "is_active": True, "description": description},
            code=code,
        )
        db.session.commit()
        for major in majors:
            prog_code = f"{code}-{''.join(w[0] for w in major.split())[:4].upper()}"
            _get_or_create(
                AcademicProgram,
                {"name": major, "department_id": dept.id,
                 "duration_years": 4, "total_credits_required": 137, "is_active": True},
                code=prog_code,
            )
    db.session.commit()
    print(f"JIT departments seeded: {len(JIT_DEPARTMENTS)}")
