import httpx
import pytest
from pydantic import ValidationError

from app.agents.groq_backends import GroqHistoryDraftingBackend, GroqReasoningBackend, _is_retryable_http_error
from app.agents.history_intake import HistoryDraftingError
from app.agents.triage import TriageBackendError
from app.schemas import CaseSummary, TriageLevel


def _case(text: str = "chest pain for two days") -> CaseSummary:
    return CaseSummary(
        symptom_text=text,
        age=45,
        duration_days=2,
        has_image=False,
        red_flag_terms=[],
    )


# -- GroqReasoningBackend -----------------------------------------------------


def test_groq_reasoning_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(TriageBackendError):
        GroqReasoningBackend(api_key=None)


def test_groq_reasoning_backend_parses_well_formed_response():
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: Symptom pattern warrants same-day evaluation."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT
    assert decision.rationale == "Symptom pattern warrants same-day evaluation."


def test_groq_reasoning_backend_defaults_to_urgent_on_unparseable_level():
    """
    Same cautious-default safety property as
    AnthropicReasoningBackend._parse: an unrecognized LEVEL value must
    fail toward the more cautious "urgent" rather than the more
    convenient "self_care" - proven here, not just assumed to carry
    over because the code was copied.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: not_a_real_level\nRATIONALE: unclear."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT


def test_groq_reasoning_backend_parse_rejects_zero_width_space_only_rationale():
    """
    Regression test for the same real bug fixed in
    AnthropicReasoningBackend._parse (see tests/test_triage.py and
    docs/INTERVIEW_NOTES.md) - GroqReasoningBackend._parse is copied
    verbatim from it (see this module's own docstring), so it shared the
    identical gap: a "RATIONALE: ​​​" (three U+200B ZERO WIDTH SPACE
    characters) response line survives `.strip()` unchanged and used to
    construct a TriageDecision whose rationale renders as completely
    blank, before TriageDecision.rationale had its own
    _visible_length-based validator in app/schemas.py.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: ​​​"

    with pytest.raises(ValidationError):
        backend._parse(raw)


def test_groq_reasoning_backend_propose_converts_invalid_rationale_to_triage_backend_error(monkeypatch):
    """
    Same proof as AnthropicReasoningBackend's own regression test: the
    real call path (propose(), not _parse() in isolation) must convert
    the ValidationError above into TriageBackendError, the same failure
    convention every other backend error in this module already uses -
    otherwise it would surface as a raw 500 through any endpoint that
    swaps in this backend.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    monkeypatch.setattr(backend, "_call", lambda case: "LEVEL: urgent\nRATIONALE: ​​​")
    case = _case()

    with pytest.raises(TriageBackendError):
        backend.propose(case)


def test_groq_reasoning_backend_parse_handles_indented_level_and_rationale_lines():
    """
    Regression test for the same real bug fixed in
    AnthropicReasoningBackend._parse (see tests/test_triage.py and
    docs/INTERVIEW_NOTES.md, Day 15) - GroqReasoningBackend._parse is
    copied verbatim from it, so it shared the identical gap: a response
    indented with leading whitespace ("  LEVEL: emergency") never matched
    `line.upper().startswith("LEVEL:")`, silently defaulting to "urgent"
    even when the model itself said "emergency" - the same dangerous
    de-escalation direction Anthropic's own backend had before the fix.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "  LEVEL: emergency\n  RATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_groq_reasoning_backend_parse_handles_zero_width_space_before_prefix():
    """
    Regression test for the same real bug fixed in
    AnthropicReasoningBackend._parse (see tests/test_triage.py and
    docs/INTERVIEW_NOTES.md, Day 17) - GroqReasoningBackend._parse now
    shares _strip_invisible with the Anthropic backend rather than a
    second, possibly-drifting copy of the same Cf-format-character
    stripping logic. A response with a ZWSP directly before "LEVEL:"
    silently missed the prefix check before the fix, defaulting to
    URGENT even though the model itself said "emergency".
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "​LEVEL: emergency\n​RATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_groq_reasoning_backend_parse_handles_zero_width_space_between_prefix_and_value():
    """
    Regression test for the same real bug fixed in
    AnthropicReasoningBackend._parse (see tests/test_triage.py and
    docs/INTERVIEW_NOTES.md, Day 18) - GroqReasoningBackend._parse is
    copied verbatim, so it shared the identical gap: Day 17's fix made
    the LEVEL:/RATIONALE: prefix check Cf-aware, but the value after the
    colon still used plain str.strip(), so a ZWSP directly after "LEVEL: "
    (e.g. "LEVEL: ​emergency") left the parsed value as "​emergency" -
    not an exact match for any TriageLevel member - and silently fell
    back to URGENT even though the model itself said "emergency".
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: ​emergency\nRATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_groq_reasoning_backend_call_converts_non_json_response_to_triage_backend_error():
    """
    Real bug, found by actually simulating a 200 response with a
    non-JSON body, not assumed away: response.raise_for_status() only
    rejects a non-2xx status code, so a 200 response whose body isn't
    valid JSON (a misconfigured proxy/gateway returning an HTML error
    page in front of Groq's OpenAI-compatible endpoint is a real,
    documented failure mode, not a contrived shape) makes
    response.json() itself raise json.JSONDecodeError - a ValueError,
    not a KeyError or IndexError, so the original
    `except (KeyError, IndexError)` around this call site never caught
    it. Mocks httpx.Client.post directly (not _call) so the real
    try/except inside _call is what's actually exercised.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://api.groq.com/x"), content=b"<html>not json</html>")

    backend._client.post = fake_post

    with pytest.raises(TriageBackendError, match="Unexpected Groq chat-completions response shape"):
        backend._call(_case())


def test_groq_reasoning_backend_propose_converts_non_json_response_to_triage_backend_error():
    """
    Same proof, one layer up: propose() (not _call() in isolation) must
    also surface this as TriageBackendError, since propose()'s own
    `except (httpx.ConnectError, httpx.TimeoutException,
    httpx.HTTPStatusError)` around _call() does not match
    json.JSONDecodeError either - it's TriageBackendError being raised
    directly inside _call() that makes this work, the same pattern
    app/agents/triage.py's AnthropicReasoningBackend._call already
    established for its own unguarded-response-shape fix (Day 11).
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://api.groq.com/x"), content=b"not json at all")

    backend._client.post = fake_post

    with pytest.raises(TriageBackendError, match="Unexpected Groq chat-completions response shape"):
        backend.propose(_case())


def test_is_retryable_http_error_retries_429_but_not_other_4xx():
    """
    Real bug, found by comparing this backend's retry policy against
    AnthropicReasoningBackend's own (app/agents/triage.py explicitly
    retries anthropic.RateLimitError - a 429): _is_retryable_http_error
    treated every 4xx, 429 included, as non-transient and left it
    unretried, silently disagreeing with the Anthropic backend on
    whether a rate-limited request gets a second chance. A 429 must be
    retried the same way a 5xx is; an ordinary 4xx (bad request, bad API
    key) must still not be, since retrying those only delays the real
    error reaching the caller.
    """
    request = httpx.Request("POST", "https://api.groq.com/x")

    rate_limited = httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, request=request))
    assert _is_retryable_http_error(rate_limited) is True

    bad_request = httpx.HTTPStatusError("400", request=request, response=httpx.Response(400, request=request))
    assert _is_retryable_http_error(bad_request) is False

    unauthorized = httpx.HTTPStatusError("401", request=request, response=httpx.Response(401, request=request))
    assert _is_retryable_http_error(unauthorized) is False

    server_error = httpx.HTTPStatusError("503", request=request, response=httpx.Response(503, request=request))
    assert _is_retryable_http_error(server_error) is True


def test_groq_reasoning_backend_call_retries_on_429_then_succeeds():
    """
    Proves the fix at the real call path, not just the predicate in
    isolation: a 429 on the first attempt, then a well-formed 200 on the
    second, must succeed via tenacity's own retry - not raise
    immediately the way pre-fix code did (reproduced directly before
    writing this fix: mocking a 429 response and counting POST attempts
    showed exactly one attempt, no retry, against the original
    `status_code >= 500`-only check).
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    request = httpx.Request("POST", "https://api.groq.com/x")
    attempts = {"n": 0}

    def fake_post(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, request=request, json={"error": "rate limited"})
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "LEVEL: urgent\nRATIONALE: Needs same-day care."}}]},
        )

    backend._client.post = fake_post

    content = backend._call(_case())

    assert attempts["n"] == 2
    assert "LEVEL: urgent" in content


def test_groq_reasoning_backend_call_gives_up_after_persistent_429s():
    """
    The retry policy still has a stop condition - a rate limit that
    never clears within stop_after_attempt(3) must still surface as a
    real error, not retry forever, exactly mirroring
    AnthropicReasoningBackend's own bounded-retry behavior on a
    persistent RateLimitError.
    """
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    request = httpx.Request("POST", "https://api.groq.com/x")
    attempts = {"n": 0}

    def fake_post(*args, **kwargs):
        attempts["n"] += 1
        return httpx.Response(429, request=request, json={"error": "rate limited"})

    backend._client.post = fake_post

    with pytest.raises(httpx.HTTPStatusError):
        backend._call(_case())

    assert attempts["n"] == 3


def test_groq_reasoning_backend_builds_prompt_in_the_shared_line_format():
    backend = GroqReasoningBackend(api_key="test-key-not-used-no-network-call")
    prompt = backend._build_prompt(_case("mild cough for two days"))

    assert "LEVEL: <self_care|clinic_visit|urgent|emergency>" in prompt
    assert "RATIONALE:" in prompt
    assert "mild cough for two days" in prompt


# -- GroqHistoryDraftingBackend ------------------------------------------------


def test_groq_history_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(HistoryDraftingError):
        GroqHistoryDraftingBackend(api_key=None)


def test_groq_history_backend_parses_well_formed_response():
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    raw = (
        "CHIEF_COMPLAINT: chest pain\n"
        "HPI: onset this morning, dull ache, worse on exertion\n"
        "PAST_HISTORY: NONE\n"
        "DRUG_ALLERGY: NONE\n"
        "FAMILY_HISTORY: father had a heart attack at 55\n"
        "PERSONAL_HISTORY: NONE\n"
        "ROS: no fever, no cough"
    )

    draft = backend._parse(raw, _case())

    assert draft.chief_complaint == "chest pain"
    assert draft.history_of_present_illness == "onset this morning, dull ache, worse on exertion"
    # "NONE" in the model's own response must become a real None, not the literal string -
    # otherwise a physician's UI would show the word "NONE" instead of a blank field.
    assert draft.past_medical_surgical_history is None
    assert draft.drug_allergy_history is None
    assert draft.family_history == "father had a heart attack at 55"
    assert draft.personal_history is None
    assert draft.review_of_systems == "no fever, no cough"


def test_groq_history_backend_falls_back_to_patient_text_on_unparseable_response():
    """
    Same fallback safety property as
    AnthropicHistoryDraftingBackend._parse: when the model's response
    doesn't follow the requested format, chief_complaint and
    history_of_present_illness must still be non-empty
    (ClinicalHistorySummary enforces min_length=3 on chief_complaint) -
    falling back to the patient's own reported text is the honest
    recovery, not a crash or a fabricated placeholder.
    """
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    case = _case("severe stomach pain since last night")

    draft = backend._parse("I'm not sure how to format this.", case)

    assert draft.chief_complaint == case.symptom_text
    assert draft.history_of_present_illness == case.symptom_text


def test_groq_history_backend_builds_prompt_in_the_shared_line_format():
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")
    prompt = backend._build_prompt(_case("persistent cough for two days"))

    assert "CHIEF_COMPLAINT:" in prompt
    assert "HPI:" in prompt
    assert "ROS:" in prompt
    assert "persistent cough for two days" in prompt


def test_groq_history_backend_call_converts_non_json_response_to_history_drafting_error():
    """
    Real bug, the SIH26047-track sibling of
    test_groq_reasoning_backend_call_converts_non_json_response_to_triage_backend_error
    above: GroqHistoryDraftingBackend._call had the exact same
    `except (KeyError, IndexError)` gap around response.json() - named as
    an unfixed, out-of-scope gap in Day 12's docs/INTERVIEW_NOTES.md
    entry, fixed now. Mocks httpx.Client.post directly (not _call) so the
    real try/except inside _call is what's actually exercised.
    """
    backend = GroqHistoryDraftingBackend(api_key="test-key-not-used-no-network-call")

    def fake_post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", "https://api.groq.com/x"), content=b"<html>not json</html>")

    backend._client.post = fake_post

    with pytest.raises(HistoryDraftingError, match="Unexpected Groq chat-completions response shape"):
        backend._call(_case())
