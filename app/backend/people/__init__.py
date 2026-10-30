"""Layer 2: staff-only directory."""
from flask import Blueprint,render_template
from flask_login import login_required
from ..security.decorators import permission_required
from ..services.people_service import directory

bp=Blueprint('people',__name__,url_prefix='/people')


@bp.get('/')
@login_required
@permission_required('view_students')
def index():
    students,teachers=directory()
    return render_template('people/index.html',students=students,teachers=teachers)
