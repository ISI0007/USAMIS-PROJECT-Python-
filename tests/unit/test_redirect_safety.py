"""Unit tests for safe-redirect validation (open-redirect prevention)."""
from app.security.decorators import is_safe_redirect


def test_relative_path_allowed():
    assert is_safe_redirect("/dashboard/")
    assert is_safe_redirect("/students/5")


def test_absolute_url_rejected():
    assert not is_safe_redirect("https://evil.example/steal")
    assert not is_safe_redirect("http://evil.example")


def test_protocol_relative_rejected():
    assert not is_safe_redirect("//evil.example")
    assert not is_safe_redirect("\\evil.example")


def test_scheme_prefix_rejected():
    assert not is_safe_redirect("javascript:alert(1)")
    assert not is_safe_redirect("data:text/html,x")


def test_empty_rejected():
    assert not is_safe_redirect("")
    assert not is_safe_redirect(None)
