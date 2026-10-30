from decimal import Decimal
from types import SimpleNamespace
from app.algorithms.academic_performance import calculate_performance
from app.algorithms.enrollment_eligibility import evaluate_enrollment


def test_fractional_credits_are_not_truncated():
    result=calculate_performance([
        {'course_code':'A','credits':1.5,'score':90,'published':True},
        {'course_code':'B','credits':2.5,'score':50,'published':True}],gpa_enabled=True)
    assert result.graded_credits == Decimal('4.0')
    assert result.weighted_average == Decimal('65.00')
    assert result.gpa == 1.81


def test_enrollment_algorithm_without_app_or_database():
    student=SimpleNamespace(enrollment_status='active')
    offering=SimpleNamespace(is_active=True,semester=SimpleNamespace(registration_open=True),course=SimpleNamespace(code='CS101',is_active=True))
    facts={'duplicate_status':None,'unmet':[],'enrolled':1,'capacity':2}
    assert evaluate_enrollment(student,offering,facts=facts).eligible
    facts['capacity']=1
    assert evaluate_enrollment(student,offering,facts=facts).reason_code == 'CAPACITY_FULL'
