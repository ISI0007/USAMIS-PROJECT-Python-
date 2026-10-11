"""External service providers, behind narrow adapter interfaces.

USAMIS never talks to a vendor SDK directly. Each integration is defined here
as a small interface plus a development **stub** implementation that records the
outbound action instead of performing network I/O. Real providers are supplied
by setting the corresponding environment variables; their credentials are read
from the environment and never stored in code or git.

Providers:

* :class:`SmsProvider` / :class:`StubSmsProvider`
* :class:`PaymentProvider` / :class:`StubPaymentProvider`
"""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass


# --------------------------------------------------------------------------
# SMS
# --------------------------------------------------------------------------
@dataclass
class SmsResult:
    ok: bool
    provider: str
    reference: str | None = None
    error: str | None = None


class SmsProvider:
    """Interface for an SMS gateway."""

    name = "base"

    def send(self, to: str, body: str) -> SmsResult:  # pragma: no cover - interface
        raise NotImplementedError


class StubSmsProvider(SmsProvider):
    """Development provider: records the send, performs no network call.

    The returned reference is deterministic so tests can assert on it.
    """

    name = "stub"

    def send(self, to: str, body: str) -> SmsResult:
        digest = hashlib.sha1(f"{to}:{body}".encode("utf-8")).hexdigest()[:16]
        return SmsResult(ok=True, provider=self.name, reference=f"stub-sms-{digest}")


# --------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------
@dataclass
class PaymentIntentResult:
    ok: bool
    provider: str
    provider_ref: str
    checkout_url: str
    error: str | None = None


class PaymentProvider:
    """Interface for an online payment gateway."""

    name = "base"

    def create_intent(self, *, reference: str, amount, currency: str = "USD",
                      description: str = "") -> PaymentIntentResult:  # pragma: no cover
        raise NotImplementedError

    def verify(self, provider_ref: str) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class StubPaymentProvider(PaymentProvider):
    """Development provider: returns a fake checkout URL and verifies locally.

    Verification succeeds for any reference the stub itself issued (tracked in
    memory and by prefix), so the full pay→callback flow is testable offline.
    """

    name = "stub"
    URL_PREFIX = "https://stub-payments.local/checkout/"

    def __init__(self) -> None:
        self._issued: set[str] = set()

    def create_intent(self, *, reference: str, amount, currency: str = "USD",
                      description: str = "") -> PaymentIntentResult:
        provider_ref = f"stub-pi-{uuid.uuid4().hex[:16]}"
        self._issued.add(provider_ref)
        return PaymentIntentResult(
            ok=True,
            provider=self.name,
            provider_ref=provider_ref,
            checkout_url=f"{self.URL_PREFIX}{provider_ref}",
        )

    def verify(self, provider_ref: str) -> bool:
        return provider_ref.startswith("stub-pi-")


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
def get_sms_provider() -> SmsProvider:
    """Return the configured SMS provider (stub unless a real one is supplied)."""
    if os.environ.get("USAMIS_SMS_PROVIDER", "stub").lower() == "stub":
        return StubSmsProvider()
    # A real provider would be constructed here from environment credentials.
    return StubSmsProvider()


def get_payment_provider() -> PaymentProvider:
    """Return the configured payment provider (stub unless a real one is supplied)."""
    if os.environ.get("USAMIS_PAYMENT_PROVIDER", "stub").lower() == "stub":
        return StubPaymentProvider()
    # A real provider would be constructed here from environment credentials.
    return StubPaymentProvider()
