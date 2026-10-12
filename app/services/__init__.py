"""Business-logic service layer.

Route handlers stay thin: they validate input, call a service, and render or
redirect. Business rules live here so they can be reused and tested.
"""
from . import audit, enrollment_service, grade_service, fee_service  # noqa: F401
from . import parent_service  # noqa: F401
