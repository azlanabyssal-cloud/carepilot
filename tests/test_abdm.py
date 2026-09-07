import base64

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.adapters.abdm import (
    AbdmAdapterError,
    RealAbdmAdapter,
    abdm_enroll,
)


def _generate_test_keypair():
    """A real RSA keypair generated fresh per test - no fixture files,
    no hardcoded "test" key that could be mistaken for a real credential.
    Returns (private_key, public_key_pem_str)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    return private_key, public_pem


def _decrypt_oaep(private_key, b64_ciphertext: str) -> str:
    """The receiving side of the same RSA-OAEP(SHA-1) scheme
    app/adapters/abdm.py's _rsa_oaep_encrypt_base64 implements - used
    here to prove the adapter's real output round-trips to the exact
    original plaintext, not merely that some ciphertext-shaped string
    was sent."""
    plaintext = private_key.decrypt(
        base64.b64decode(b64_ciphertext),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None),
    )
    return plaintext.decode("utf-8")


def _fake_cert_response(public_pem: str):
    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", "https://x"),
            json={"publicKey": public_pem, "encryptionAlgorithm": "RSA/ECB/OAEPWithSHA-1AndMGF1Padding"},
        )

    return fake_get


class FakeAbdmAdapter:
    """Test double implementing the AbdmAdapter protocol - no network call."""

    def __init__(self, transaction_id: str, abha_number: str) -> None:
        self._transaction_id = transaction_id
        self._abha_number = abha_number
        self.request_otp_calls: list[str] = []
        self.verify_otp_calls: list[tuple[str, str]] = []

    def request_abha_otp(self, identifier: str) -> str:
        self.request_otp_calls.append(identifier)
        return self._transaction_id

    def verify_abha_otp(self, transaction_id: str, otp: str) -> str:
        self.verify_otp_calls.append((transaction_id, otp))
        return self._abha_number


def test_abdm_enroll_chains_request_otp_into_verify_otp():
    fake = FakeAbdmAdapter(transaction_id="txn-abc-123", abha_number="12-3456-7890-1234")
    identifier = "9999999999"

    result = abdm_enroll(fake, identifier, otp_provider=lambda: "246810")

    assert result == "12-3456-7890-1234"
    # Proven, not just claimed: verify_abha_otp received request_abha_otp's
    # returned transaction ID, not the raw identifier passed in.
    assert fake.request_otp_calls == [identifier]
    assert fake.verify_otp_calls == [(fake._transaction_id, "246810")]


def test_abdm_enroll_calls_otp_provider_exactly_once_after_requesting_otp():
    fake = FakeAbdmAdapter(transaction_id="txn-xyz-999", abha_number="98-7654-3210-9876")
    calls: list[str] = []

    def otp_provider() -> str:
        calls.append("called")
        return "135790"

    result = abdm_enroll(fake, "8888888888", otp_provider=otp_provider)

    assert result == "98-7654-3210-9876"
    assert calls == ["called"]
    assert fake.verify_otp_calls == [("txn-xyz-999", "135790")]


def test_abdm_enroll_returns_abha_number_type():
    fake = FakeAbdmAdapter(transaction_id="txn-1", abha_number="11-2222-3333-4444")
    result = abdm_enroll(fake, "7777777777", otp_provider=lambda: "000000")
    assert isinstance(result, str)
    assert result == "11-2222-3333-4444"


def test_real_adapter_requires_client_id(monkeypatch):
    monkeypatch.delenv("ABDM_CLIENT_ID", raising=False)
    monkeypatch.setenv("ABDM_CLIENT_SECRET", "test-secret-not-used-no-network-call")
    with pytest.raises(AbdmAdapterError):
        RealAbdmAdapter(client_id=None, client_secret=None)


def test_real_adapter_requires_client_secret(monkeypatch):
    monkeypatch.setenv("ABDM_CLIENT_ID", "test-id-not-used-no-network-call")
    monkeypatch.delenv("ABDM_CLIENT_SECRET", raising=False)
    with pytest.raises(AbdmAdapterError):
        RealAbdmAdapter(client_id=None, client_secret=None)


def test_real_adapter_requires_both_credentials_missing(monkeypatch):
    monkeypatch.delenv("ABDM_CLIENT_ID", raising=False)
    monkeypatch.delenv("ABDM_CLIENT_SECRET", raising=False)
    with pytest.raises(AbdmAdapterError) as exc_info:
        RealAbdmAdapter(client_id=None, client_secret=None)
    # Clear about *why* it failed, not just that it failed - same bar as
    # BhashiniAdapterError's message in app/adapters/bhashini.py.
    assert "ABDM_CLIENT_ID" in str(exc_info.value)
    assert "ABDM_CLIENT_SECRET" in str(exc_info.value)


def test_real_adapter_constructs_with_explicit_credentials():
    # No network call happens at construction time - only at
    # request_abha_otp()/verify_abha_otp() call time, same lazy pattern
    # as RealBhashiniAdapter.
    adapter = RealAbdmAdapter(client_id="explicit-id", client_secret="explicit-secret")
    assert adapter is not None


def test_real_adapter_accepts_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("ABDM_CLIENT_ID", "env-id-not-used-no-network-call")
    monkeypatch.setenv("ABDM_CLIENT_SECRET", "env-secret-not-used-no-network-call")
    adapter = RealAbdmAdapter()
    assert adapter is not None


# -- non-JSON response bodies, the same validation-boundary failure class ------
# already fixed three times in the core pipeline this week (Anthropic and
# Groq triage backends, the Bhashini adapter) - audited here for the first
# time against this file's own two response.json() call sites.


def test_request_abha_otp_converts_non_json_response_to_abdm_adapter_error(monkeypatch):
    """
    Real bug: request_abha_otp() called response.json() with only
    `except KeyError` around it. response.raise_for_status() only rejects
    a non-2xx status code, so a 200 response whose body isn't valid JSON
    at all (a misconfigured proxy/gateway returning an HTML error page -
    the same real-world failure mode already fixed for the Groq and
    Bhashini adapters) made response.json() itself raise
    json.JSONDecodeError - a ValueError, not a KeyError - so it propagated
    raw instead of becoming a clean AbdmAdapterError. Mocks httpx.get (the
    public-certificate fetch, which now runs first) and httpx.post
    directly (not the method) so the real try/except is what's exercised.
    """
    _, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"<html>not json</html>")

    monkeypatch.setattr(httpx, "post", fake_post)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="Unexpected request-OTP response shape"):
        adapter.request_abha_otp("1234-5678-9012")


def test_verify_abha_otp_converts_non_json_response_to_abdm_adapter_error(monkeypatch):
    """Same proof, for verify_abha_otp()'s own separate except clause -
    which already caught (KeyError, TypeError) but not json.JSONDecodeError
    either."""
    _, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"not json")

    monkeypatch.setattr(httpx, "post", fake_post)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="Unexpected verify-OTP response shape"):
        adapter.verify_abha_otp("txn-123", "246810")


# -- RSA-OAEP encryption of sensitive fields (Aadhaar/mobile identifier, --------
# OTP value) - the real, second-pass fix for this file's own named
# "known simplification": ABDM's real V3 flow requires both fields
# encrypted with a public key fetched from /profile/public/certificate,
# and the original code sent both as plain fields.


def test_request_abha_otp_encrypts_the_identifier_with_the_fetched_public_key(monkeypatch):
    """
    Proves real, correct encryption - not merely that some ciphertext-
    shaped string was sent. Generates a real RSA keypair, serves its
    public half back to the adapter as the /profile/public/certificate
    response, captures the actual outgoing request body, and decrypts
    the loginId field with the matching private key to assert it
    recovers the exact original identifier. If the encryption were
    wrong (wrong padding, wrong hash, encrypting the wrong field, or not
    encrypting at all) this test fails on the decrypt step or the
    equality assertion, not just on "was some field present."
    """
    private_key, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    captured = {}

    def capturing_post(*args, **kwargs):
        captured.update(kwargs.get("json", {}))
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), json={"txnId": "txn-abc-123"})

    monkeypatch.setattr(httpx, "post", capturing_post)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    txn_id = adapter.request_abha_otp("999988887777")

    assert txn_id == "txn-abc-123"
    assert captured["loginId"] != "999988887777"  # not sent in plain text
    assert _decrypt_oaep(private_key, captured["loginId"]) == "999988887777"
    # otpSystem/scope are not sensitive - unchanged, still sent in plain.
    assert captured["otpSystem"] == "aadhaar"


def test_verify_abha_otp_encrypts_the_otp_value_with_the_fetched_public_key(monkeypatch):
    """Same proof as above, for verify_abha_otp()'s own otpValue field -
    ABDM's V3 flow requires the OTP itself encrypted too, not just the
    identifier, a change from older API versions that sent it in plain
    text. txnId is not sensitive and must stay unencrypted."""
    private_key, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    captured = {}

    def capturing_post(*args, **kwargs):
        captured.update(kwargs.get("json", {}))
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://x"),
            json={"ABHAProfile": {"ABHANumber": "12-3456-7890-1234"}},
        )

    monkeypatch.setattr(httpx, "post", capturing_post)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    abha_number = adapter.verify_abha_otp("txn-123", "246810")

    assert abha_number == "12-3456-7890-1234"
    otp_field = captured["authData"]["otp"]
    assert otp_field["otpValue"] != "246810"  # not sent in plain text
    assert _decrypt_oaep(private_key, otp_field["otpValue"]) == "246810"
    assert otp_field["txnId"] == "txn-123"  # not sensitive, stays plain


def test_fetch_public_key_converts_non_json_certificate_response_to_abdm_adapter_error(monkeypatch):
    """The new /profile/public/certificate call site has the exact same
    validation-boundary shape as every response.json() call site already
    audited this session - proven guarded from day one, not found broken
    and fixed later, since this call site didn't exist before today."""

    def fake_get(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", "https://x"), content=b"not json")

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="Unexpected public-certificate response shape"):
        adapter.request_abha_otp("1234-5678-9012")


def test_fetch_public_key_rejects_a_response_missing_the_public_key_field(monkeypatch):
    def fake_get(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", "https://x"), json={"unexpected": "shape"})

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="Unexpected public-certificate response shape"):
        adapter.request_abha_otp("1234-5678-9012")


def test_fetch_public_key_rejects_a_null_public_key_field(monkeypatch):
    """
    Real bug, found by this session's own brutal self-review of its new
    code before it shipped, not by a later incident: "publicKey" present
    but null (or any other non-string JSON value) is valid JSON and
    passes a plain `except KeyError`, but
    data["publicKey"].encode("ascii") then raises AttributeError, not
    KeyError/ValueError - confirmed by reproducing it directly with
    {"publicKey": None} before this except clause was widened to include
    AttributeError/TypeError.
    """

    def fake_get(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", "https://x"), json={"publicKey": None})

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="Unexpected public-certificate response shape"):
        adapter.request_abha_otp("1234-5678-9012")


# -- the retry decorator that never actually retried -----------------------
# A real, structural bug found by reasoning about control flow, not by
# simulating a specific bad response: request_abha_otp/verify_abha_otp
# were @retry-decorated, but their OWN except clause caught exactly the
# exception types the decorator was watching for (httpx.ConnectError,
# httpx.ReadTimeout) and converted them to AbdmAdapterError *inside* the
# same decorated function - so tenacity's retry predicate never actually
# saw a retryable exception type, and the retry silently never fired,
# despite an error message that explicitly claimed "failed after
# retries." Confirmed broken before the fix by counting real call
# attempts against the pre-fix code (1 attempt, not the configured 3).


def test_request_abha_otp_actually_retries_on_connection_failure(monkeypatch):
    """
    The single most load-bearing regression test in this file: proves
    the @retry decorator on the low-level _post_request_otp call
    actually makes multiple attempts on a transient connection failure,
    not just that the final AbdmAdapterError message reads correctly.
    Counts real call attempts against a mock that fails every time -
    stop_after_attempt(3) means exactly 3, not 1.
    """
    _, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    call_count = {"n": 0}

    def always_fails(*args, **kwargs):
        call_count["n"] += 1
        raise httpx.ConnectError("simulated transient connection failure")

    monkeypatch.setattr(httpx, "post", always_fails)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="ABDM request-OTP call failed after retries"):
        adapter.request_abha_otp("1234-5678-9012")

    assert call_count["n"] == 3


def test_verify_abha_otp_actually_retries_on_connection_failure(monkeypatch):
    """Same proof as above, for verify_abha_otp's own separate
    @retry-decorated _post_verify_otp call - a separate decorated
    function with the exact same bug, fixed the same way."""
    _, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    call_count = {"n": 0}

    def always_fails(*args, **kwargs):
        call_count["n"] += 1
        raise httpx.ConnectError("simulated transient connection failure")

    monkeypatch.setattr(httpx, "post", always_fails)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    with pytest.raises(AbdmAdapterError, match="ABDM verify-OTP call failed after retries"):
        adapter.verify_abha_otp("txn-123", "246810")

    assert call_count["n"] == 3


def test_request_abha_otp_succeeds_after_a_transient_failure_then_a_success(monkeypatch):
    """The other half of proving retry actually works: not just that it
    tries 3 times before giving up, but that a transient failure
    followed by a real success is recovered from cleanly - the actual
    point of having retry logic at all."""
    _, public_pem = _generate_test_keypair()
    monkeypatch.setattr(httpx, "get", _fake_cert_response(public_pem))

    call_count = {"n": 0}

    def fails_once_then_succeeds(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.ConnectError("simulated one-off connection blip")
        return httpx.Response(200, request=httpx.Request("POST", "https://x"), json={"txnId": "txn-recovered"})

    monkeypatch.setattr(httpx, "post", fails_once_then_succeeds)

    adapter = RealAbdmAdapter(client_id="u", client_secret="k")
    txn_id = adapter.request_abha_otp("1234-5678-9012")

    assert txn_id == "txn-recovered"
    assert call_count["n"] == 2
