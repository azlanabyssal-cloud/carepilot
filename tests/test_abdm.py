import pytest

from app.adapters.abdm import (
    AbdmAdapterError,
    RealAbdmAdapter,
    abdm_enroll,
)


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
