"""
ABDM (Ayushman Bharat Digital Mission) ABHA adapter - M1 milestone only.

SIH26047's Module D calls for pushing structured history to a hospital
HIS/EMR and linking it to the patient's ABHA Personal Health Record via
FHIR APIs. That is a real, multi-week integration (ABHA creation, then
the FHIR bundle push, then the HIS/EMR linkage record - see this
project's own research dossier). This module implements only the first,
most foundational step of that pipeline: M1, ABHA ID creation via the
ABDM sandbox's Aadhaar-OTP enrollment flow. It does NOT implement FHIR
bundle construction, HIS/EMR push, or Personal Health Record linkage -
those are M2/M3 and are out of scope here, deliberately, not by
oversight.

Same shape as app/adapters/bhashini.py on purpose: a Protocol so callers
can be unit-tested against a fake backend with no network call, a
concrete real implementation that fails fast with a clear custom error
when credentials are missing, and a pure orchestration function that
chains the two adapter calls. See tests/test_abdm.py.

VERIFICATION STATUS - read this before trusting anything below:
This environment has no real ABDM_CLIENT_ID / ABDM_CLIENT_SECRET.
Registration for ABDM sandbox access was never completed in this
environment, and no live network call to abhasbx.abdm.gov.in was made
or could be made while building this. The base URL
(https://abhasbx.abdm.gov.in/abha/api/v3) is ABDM's real, publicly
documented sandbox base. The two endpoint paths used below -
/enrollment/request/otp and /enrollment/enrol/byAadhaar - are the
paths ABDM's public sandbox documentation and Postman collections
describe for the Aadhaar-OTP ABHA-creation flow, but the exact request
and response field names implemented here (loginId/otpSystem/scope on
the request side, ABHAProfile/ABHANumber on the response side) were
transcribed from that public documentation, not confirmed against a
live response in this environment. Two things in particular are known
simplifications, called out explicitly rather than hidden:
  1. ABDM's real Aadhaar-OTP request encrypts the Aadhaar/mobile number
     with an RSA public key fetched from a separate ABDM certs
     endpoint before it is sent. That encryption step is not
     implemented here - the identifier is sent as a plain field. Wiring
     in real encryption is exactly the kind of gap this section exists
     to flag, not a claim that this is production-ready.
  2. Whether the sandbox expects ABDM_CLIENT_ID/ABDM_CLIENT_SECRET as
     the literal request headers used below versus exchanged first for
     a bearer token via a separate gateway/session endpoint was not
     confirmed either way.
What IS verified: the orchestration logic (abdm_enroll chaining
request_abha_otp -> otp_provider -> verify_abha_otp), the
credential-missing fail-fast path, and that the request bodies match
the shape described in public ABDM sandbox documentation - all covered
by tests/test_abdm.py using a fake adapter, zero network calls. Do not
present this as "tested against the real API" - it hasn't been, and
can't be, in this environment.
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ABDM_SANDBOX_BASE_URL = "https://abhasbx.abdm.gov.in/abha/api/v3"

# Unverified in this environment - see the module docstring's
# Verification Status section, point 2.
REQUEST_OTP_URL = f"{ABDM_SANDBOX_BASE_URL}/enrollment/request/otp"
VERIFY_OTP_URL = f"{ABDM_SANDBOX_BASE_URL}/enrollment/enrol/byAadhaar"


class AbdmAdapterError(RuntimeError):
    """Raised when the ABDM adapter fails, including after retries are exhausted."""


class AbdmAdapter(Protocol):
    """Anything that can run ABHA M1 enrollment: request an OTP, then verify it.

    A Protocol, not a concrete base class, so abdm_enroll() can be
    unit-tested against a fake adapter - no network call, no
    credentials, no real OTP required. See tests/test_abdm.py.
    """

    def request_abha_otp(self, identifier: str) -> str:
        """Trigger an OTP to the given Aadhaar/mobile number. Returns a transaction ID."""
        ...

    def verify_abha_otp(self, transaction_id: str, otp: str) -> str:
        """Submit the OTP for a transaction. Returns the resulting ABHA number."""
        ...


class RealAbdmAdapter:
    """Real adapter: calls the ABDM sandbox's Aadhaar-OTP ABHA enrollment flow (M1 only).

    See the module docstring's Verification Status section - this has
    never been exercised against ABDM's real sandbox in this
    environment. The request/response shape is transcribed from public
    ABDM sandbox documentation, not confirmed first-hand.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        resolved_client_id = client_id or os.environ.get("ABDM_CLIENT_ID")
        resolved_client_secret = client_secret or os.environ.get("ABDM_CLIENT_SECRET")
        if not resolved_client_id or not resolved_client_secret:
            raise AbdmAdapterError(
                "ABDM_CLIENT_ID and/or ABDM_CLIENT_SECRET is not set. Export both in the "
                "environment or pass client_id/client_secret explicitly - never hardcode "
                "credentials in source or commit them."
            )
        self._client_id = resolved_client_id
        self._client_secret = resolved_client_secret
        self._timeout = timeout

    def _auth_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Client-Id": self._client_id,
            "Client-Secret": self._client_secret,
        }

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def request_abha_otp(self, identifier: str) -> str:
        body = {
            "loginId": identifier,
            "otpSystem": "aadhaar",
            "scope": ["abha-enrol"],
        }
        try:
            response = httpx.post(
                REQUEST_OTP_URL, json=body, headers=self._auth_headers(), timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["txnId"]
        except httpx.HTTPStatusError as exc:
            raise AbdmAdapterError(f"ABDM request-OTP call failed: {exc}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise AbdmAdapterError(f"ABDM request-OTP call failed after retries: {exc}") from exc
        except KeyError as exc:
            raise AbdmAdapterError(f"Unexpected request-OTP response shape: {exc}") from exc

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def verify_abha_otp(self, transaction_id: str, otp: str) -> str:
        body = {
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "txnId": transaction_id,
                    "otpValue": otp,
                },
            }
        }
        try:
            response = httpx.post(
                VERIFY_OTP_URL, json=body, headers=self._auth_headers(), timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["ABHAProfile"]["ABHANumber"]
        except httpx.HTTPStatusError as exc:
            raise AbdmAdapterError(f"ABDM verify-OTP call failed: {exc}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise AbdmAdapterError(f"ABDM verify-OTP call failed after retries: {exc}") from exc
        except (KeyError, TypeError) as exc:
            raise AbdmAdapterError(f"Unexpected verify-OTP response shape: {exc}") from exc


def abdm_enroll(adapter: AbdmAdapter, identifier: str, otp_provider: Callable[[], str]) -> str:
    """
    Pure orchestration, no I/O of its own: request an OTP for the given
    Aadhaar/mobile identifier, obtain the OTP via otp_provider (in a
    real UI this is "wait for the user to type the OTP they received
    on their phone" - injected here as a callable so this is testable
    without a real OTP flow), then verify it. Returns the resulting
    ABHA number. Takes the adapter as a parameter rather than
    constructing one internally, same reason bhashini_to_intake(adapter,
    audio_bytes) does in app/adapters/bhashini.py - it makes this
    function testable with a fake, no network or credentials required.
    """
    transaction_id = adapter.request_abha_otp(identifier)
    otp = otp_provider()
    return adapter.verify_abha_otp(transaction_id, otp)
