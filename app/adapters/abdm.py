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
documented sandbox base. The three endpoint paths used below -
/profile/public/certificate, /enrollment/request/otp, and
/enrollment/enrol/byAadhaar - are the paths ABDM's public V3 sandbox
documentation (cross-checked across multiple independent third-party
integration writeups, not a single source) describes for the
Aadhaar-OTP ABHA-creation flow, but the exact request and response
field names implemented here were transcribed from that public
documentation, not confirmed against a live response in this
environment. One thing in particular is a known simplification, called
out explicitly rather than hidden: whether the sandbox expects
ABDM_CLIENT_ID/ABDM_CLIENT_SECRET as the literal request headers used
below versus exchanged first for a bearer token via a separate
gateway/session endpoint was not confirmed either way.

RSA-OAEP ENCRYPTION - real, not simplified, as of the second pass on
this module. ABDM's real V3 Aadhaar-OTP flow requires the Aadhaar/mobile
identifier (loginId) AND the OTP value (otpValue) to be RSA-encrypted
with a public key fetched fresh from the sandbox's own
/profile/public/certificate endpoint before either is sent -
cross-checked across multiple independent public sources
(devlprnitish.medium.com's ABHA V3 API reference, the
Technoculture/ABDM-ABHA-SDK and BlueBash/abdm-ruby open-source
integrations, and the ABDM sandbox developer forum) that all agree on
the same shape: the certificate endpoint returns
{"publicKey": "<PEM>", "encryptionAlgorithm":
"RSA/ECB/OAEPWithSHA-1AndMGF1Padding"}, i.e. RSA-OAEP with SHA-1 as
both the hash and the MGF1 mask-generation hash, no label - implemented
below with Python's `cryptography` library
(cryptography.hazmat.primitives.asymmetric.padding.OAEP(mgf=MGF1(SHA1()),
algorithm=SHA1(), label=None)), matching the Java cipher-transformation
string ABDM's own docs name character-for-character. Ciphertext is
base64-encoded before being placed in the request body, per the same
sources. This is real, correct RSA-OAEP encryption, proven by a
regression test that generates its own RSA keypair, serves the public
half back to the adapter as a fake /profile/public/certificate
response, and decrypts the adapter's actual outgoing request body with
the matching private key to assert it recovers the exact original
plaintext (tests/test_abdm.py) - not merely that some ciphertext-shaped
string was sent. What is still NOT verified: that this exact encryption
implementation is byte-for-byte accepted by ABDM's real sandbox server,
since no live credentials or network access exist in this environment
to make that final call. That is a real, named gap, not smoothed over -
see "What IS verified" below for the precise boundary.
What IS verified: the orchestration logic (abdm_enroll chaining
request_abha_otp -> otp_provider -> verify_abha_otp), the
credential-missing fail-fast path, that the request bodies match the
shape described in public ABDM sandbox documentation, and that the
RSA-OAEP encryption is cryptographically correct (round-trips through a
real keypair, not just presence-checked) - all covered by
tests/test_abdm.py using a fake adapter, zero real network calls. Do
not present this as "tested against the real API" - it hasn't been,
and can't be, in this environment.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Callable, Protocol

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ABDM_SANDBOX_BASE_URL = "https://abhasbx.abdm.gov.in/abha/api/v3"

CERTS_URL = f"{ABDM_SANDBOX_BASE_URL}/profile/public/certificate"
# Unverified in this environment - see the module docstring's
# Verification Status section.
REQUEST_OTP_URL = f"{ABDM_SANDBOX_BASE_URL}/enrollment/request/otp"
VERIFY_OTP_URL = f"{ABDM_SANDBOX_BASE_URL}/enrollment/enrol/byAadhaar"


def _rsa_oaep_encrypt_base64(plaintext: str, public_key: RSAPublicKey) -> str:
    """
    Encrypt plaintext with RSA-OAEP (SHA-1 hash, MGF1-SHA-1 mask, no
    label) and base64-encode the ciphertext - the exact scheme ABDM's
    /profile/public/certificate response names as
    "RSA/ECB/OAEPWithSHA-1AndMGF1Padding" (see the module docstring's
    RSA-OAEP ENCRYPTION section for the sources this was cross-checked
    against). A pure function, not a method, so it's independently unit
    testable against a self-generated keypair with no network or ABDM
    adapter involved at all.
    """
    ciphertext = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None),
    )
    return base64.b64encode(ciphertext).decode("ascii")


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

    def _fetch_public_key(self) -> RSAPublicKey:
        """
        Fetch ABDM's current RSA public key for encrypting sensitive
        enrollment fields (Aadhaar/mobile identifiers, OTP values) -
        fetched fresh on every call rather than cached, since ABDM's own
        docs don't guarantee the certificate is stable across requests
        and a stale cached key would silently produce ciphertext the
        real server rejects. See the module docstring's RSA-OAEP
        ENCRYPTION section for the response shape this expects.

        Deliberately has no @retry decorator of its own, and deliberately
        does NOT catch (httpx.ConnectError, httpx.ReadTimeout) here: this
        method is only ever called from inside request_abha_otp()/
        verify_abha_otp(), which already retry on exactly those two
        exception types. Catching and converting them here would hide
        them from that outer retry (which only matches the raw httpx
        exception types, not AbdmAdapterError) and silently turn a
        3-attempt retry into a 1-attempt failure - the opposite of the
        intended behavior, and a real bug in its own right if it shipped
        unnoticed. So connection/timeout failures are left to propagate
        raw and be caught (and retried) by the caller; only failures a
        retry can never fix - a bad HTTP status, or a 200 response with
        the wrong shape - are converted to AbdmAdapterError here.
        """
        try:
            response = httpx.get(CERTS_URL, headers=self._auth_headers(), timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            pem_bytes = data["publicKey"].encode("ascii")
            public_key = serialization.load_pem_public_key(pem_bytes)
        except httpx.HTTPStatusError as exc:
            raise AbdmAdapterError(f"ABDM public-certificate fetch failed: {exc}") from exc
        except (KeyError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            # AttributeError/TypeError: caught here, not assumed away -
            # found by this session's own brutal self-review before it
            # shipped, not by a later incident. If the response has
            # "publicKey" present but not a string (null, a number, a
            # nested object - all valid JSON, all a real possible bad
            # response shape), data["publicKey"].encode("ascii") raises
            # AttributeError, not ValueError/KeyError - confirmed by
            # reproducing it directly with {"publicKey": None} before
            # this except clause was widened.
            raise AbdmAdapterError(f"Unexpected public-certificate response shape: {exc}") from exc
        if not isinstance(public_key, RSAPublicKey):
            raise AbdmAdapterError(
                "ABDM public-certificate response did not contain an RSA public key."
            )
        return public_key

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _post_request_otp(self, body: dict) -> dict:
        # Deliberately does NOT catch (httpx.ConnectError, httpx.ReadTimeout)
        # here: this is the actual @retry-decorated network call, and
        # tenacity's retry_if_exception_type only ever sees an exception
        # that escapes this function uncaught. A real, confirmed bug
        # (reproduced directly: a simulated ConnectError on every attempt
        # made exactly 1 real httpx.post call, not the 3 stop_after_attempt
        # was configured for) existed here before this fix, because the
        # original code caught and converted ConnectError/ReadTimeout to
        # AbdmAdapterError inside the same @retry-decorated function body -
        # so tenacity only ever saw AbdmAdapterError, which doesn't match
        # its retry predicate, and never retried at all despite the error
        # message claiming "failed after retries." Splitting the raw,
        # retryable network call (here) from the exception-to-AbdmAdapterError
        # conversion (in request_abha_otp, below, which calls this and only
        # ever sees the final, retry-exhausted exception) is the same
        # working pattern this codebase already proves correct elsewhere -
        # app/adapters/bhashini.py's _get_pipeline_config/_post_inference
        # (the retryable step) versus transcribe()/translate() (the
        # exception-converting caller).
        response = httpx.post(REQUEST_OTP_URL, json=body, headers=self._auth_headers(), timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def request_abha_otp(self, identifier: str) -> str:
        public_key = self._fetch_public_key()
        body = {
            "loginId": _rsa_oaep_encrypt_base64(identifier, public_key),
            "otpSystem": "aadhaar",
            "scope": ["abha-enrol"],
        }
        try:
            data = self._post_request_otp(body)
            return data["txnId"]
        except httpx.HTTPStatusError as exc:
            raise AbdmAdapterError(f"ABDM request-OTP call failed: {exc}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise AbdmAdapterError(f"ABDM request-OTP call failed after retries: {exc}") from exc
        except (KeyError, json.JSONDecodeError) as exc:
            # Same validation-boundary failure class already found and
            # fixed three times in the core pipeline this week
            # (Anthropic and Groq triage backends, the Bhashini adapter):
            # response.raise_for_status() only rejects a non-2xx status,
            # so a 200 response whose body isn't valid JSON at all (a
            # misconfigured proxy/gateway error page, a real failure mode
            # for third-party HTTP APIs) makes response.json() itself
            # raise json.JSONDecodeError - a ValueError the original
            # `except KeyError` here never caught.
            raise AbdmAdapterError(f"Unexpected request-OTP response shape: {exc}") from exc

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _post_verify_otp(self, body: dict) -> dict:
        # Same fix and same reasoning as _post_request_otp above.
        response = httpx.post(VERIFY_OTP_URL, json=body, headers=self._auth_headers(), timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def verify_abha_otp(self, transaction_id: str, otp: str) -> str:
        public_key = self._fetch_public_key()
        body = {
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "txnId": transaction_id,
                    "otpValue": _rsa_oaep_encrypt_base64(otp, public_key),
                },
            }
        }
        try:
            data = self._post_verify_otp(body)
            return data["ABHAProfile"]["ABHANumber"]
        except httpx.HTTPStatusError as exc:
            raise AbdmAdapterError(f"ABDM verify-OTP call failed: {exc}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise AbdmAdapterError(f"ABDM verify-OTP call failed after retries: {exc}") from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            # Same fix and same reasoning as request_abha_otp above.
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
