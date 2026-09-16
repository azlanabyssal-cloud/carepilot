import pytest
from pydantic import ValidationError

from app.agents.triage import (
    AnthropicReasoningBackend,
    DeterministicFallbackReasoningBackend,
    TriageBackendError,
    run_triage_reasoning,
)
from app.schemas import CaseSummary, TriageDecision, TriageLevel


class FakeBackend:
    """Test double implementing the ReasoningBackend protocol - no network call."""

    def __init__(self, decision: TriageDecision) -> None:
        self._decision = decision
        self.called = False

    def propose(self, case: CaseSummary) -> TriageDecision:
        self.called = True
        return self._decision


def _case(text: str, red_flags: list[str] | None = None) -> CaseSummary:
    return CaseSummary(
        symptom_text=text,
        age=30,
        duration_days=1,
        has_image=False,
        red_flag_terms=red_flags or [],
    )


def test_red_flag_case_short_circuits_without_calling_backend():
    fake = FakeBackend(TriageDecision(level=TriageLevel.SELF_CARE, rationale="should not be used", confidence=0.5))
    case = _case("chest pain", red_flags=["chest pain"])

    decision = run_triage_reasoning(case, fake)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.confidence == 1.0
    assert fake.called is False  # this is the actual point of the design - proven, not claimed


def test_ordinary_case_delegates_to_backend():
    fake = FakeBackend(
        TriageDecision(level=TriageLevel.CLINIC_VISIT, rationale="persistent mild symptom", confidence=0.7)
    )
    case = _case("mild cough for two days")

    decision = run_triage_reasoning(case, fake)

    assert decision.level == TriageLevel.CLINIC_VISIT
    assert fake.called is True


def test_anthropic_backend_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(TriageBackendError):
        AnthropicReasoningBackend(api_key=None)


def test_anthropic_backend_parses_well_formed_response():
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: Symptom pattern warrants same-day evaluation."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT
    assert decision.rationale == "Symptom pattern warrants same-day evaluation."


def test_anthropic_backend_defaults_to_urgent_on_unparseable_level():
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: not_a_real_level\nRATIONALE: unclear."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT


def test_anthropic_backend_parse_rejects_zero_width_space_only_rationale():
    """
    Regression test for a real bug, the same failure class as
    ClinicalHistorySummary.chief_complaint/history_of_present_illness
    (see docs/INTERVIEW_NOTES.md, Days 8-9): _parse()'s
    `line.split(":", 1)[1].strip()` on a "RATIONALE: ​​​" (three U+200B
    ZERO WIDTH SPACE characters) response line leaves the invisible
    characters untouched - non-empty per str.strip() - so before
    TriageDecision.rationale had its own _visible_length-based validator
    (app/schemas.py), this constructed a TriageDecision whose rationale
    renders as completely blank. _parse() itself has no try/except, so
    the underlying pydantic.ValidationError surfaces directly here -
    see test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error
    below for proof that propose() (the real call path) converts it to
    the same TriageBackendError every other backend failure already is.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: urgent\nRATIONALE: ​​​"

    with pytest.raises(ValidationError):
        backend._parse(raw)


def test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error(monkeypatch):
    """
    Proves propose() - the actual method run_triage_reasoning() calls,
    not _parse() in isolation - catches the ValidationError above and
    raises TriageBackendError instead, the same failure convention every
    other backend error in this module already uses. Without this,
    app/main.py's _run_triage (which only catches TriageBackendError,
    not ValidationError) would let this surface as a raw 500 instead of
    the clean 503 test_main.py's
    test_assess_ordinary_case_returns_503_not_500_when_backend_rationale_is_invisible_only
    proves it now returns.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    monkeypatch.setattr(backend, "_call", lambda case: "LEVEL: urgent\nRATIONALE: ​​​")
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError):
        backend.propose(case)


def test_anthropic_backend_parse_handles_indented_level_and_rationale_lines():
    """
    Regression test for a real bug, found by simulating realistic
    model-formatting irregularity rather than assuming the exact
    prompted shape - the same discipline that already found the
    red-flag-scanner whitespace bug (docs/INTERVIEW_NOTES.md, Day 14),
    applied one layer further down the pipeline. _parse() matched each
    line with `line.upper().startswith("LEVEL:")`, with no leading
    whitespace stripped first, so a response indented with even one
    leading space - the kind of formatting a model can add on its own
    inside a markdown bullet, a numbered step, or a code-fence remnant,
    despite the prompt asking for exactly two bare lines - never matched
    either prefix. Reproduced directly before the fix: both branches
    silently missed, level stayed at the URGENT default, and rationale
    fell back to the entire raw two-line response instead of just the
    intended sentence. The dangerous direction: a model that itself
    judged "emergency" got silently DE-escalated to "urgent" purely
    because of indentation - the opposite of this project's own named
    priority metric, recall on emergency-flagged cases.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "  LEVEL: emergency\n  RATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY


def test_anthropic_backend_parse_handles_zero_width_space_before_prefix():
    """
    Regression test for a real bug, one layer past Day 15's leading-
    whitespace fix (docs/INTERVIEW_NOTES.md, Day 17): `line.strip()`
    only strips true Unicode whitespace, not Unicode *format* characters
    (category "Cf" - ZERO WIDTH SPACE U+200B and friends), the exact
    "Cf is not real content" gap Day 16 already found and fixed in
    app/agents/intake.py's scan_red_flags() and app/schemas.py's
    _visible_length, but named there as a real, unfixed sibling gap in
    this exact function. A response with a ZWSP directly before "LEVEL:"
    (e.g. "​LEVEL: emergency") - a realistic artifact of the same
    predictive-text/IME/copy-paste sources Day 16 documented, just landing
    at the very start of the model's own response instead of mid-word in
    user-typed text - silently missed the prefix check, defaulting to the
    URGENT fallback even though the model itself said "emergency": the
    exact dangerous de-escalation direction Day 15 already fixed for plain
    leading spaces, reproduced again here with an invisible character
    instead. Reproduced directly before the fix (this exact input
    returned TriageLevel.URGENT, not EMERGENCY) before writing the fix.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "​LEVEL: emergency\n​RATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_anthropic_backend_parse_zero_width_space_fix_does_not_overmatch():
    """
    Guards the Day 17 fix against over-matching: a ZWSP genuinely inside
    the word "LEVEL" (not adjacent to real whitespace at all) still
    correctly fails to parse and falls back to the cautious URGENT
    default - _strip_invisible only strips leading/trailing Cf
    characters, it does not delete them from the interior of a line, so
    this is not silently "fixed" into matching too.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LE​VEL: emergency\nRATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.URGENT
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_anthropic_backend_parse_handles_zero_width_space_between_prefix_and_value():
    """
    Regression test for a real bug, found one token past Day 17's own fix
    (docs/INTERVIEW_NOTES.md, Day 17): Day 17 made the LEVEL:/RATIONALE:
    *prefix* check Cf-aware via _strip_invisible, but the *value* pulled
    out after the colon (`stripped_line.split(":", 1)[1].strip().lower()`)
    still used plain str.strip(), which leaves Unicode category "Cf"
    characters untouched. A ZERO WIDTH SPACE sitting directly after
    "LEVEL: " and before the actual word (e.g. "LEVEL: ​emergency") left
    the parsed value as "​emergency" - not an exact match for any
    TriageLevel member - so `TriageLevel(value)` raised the caught
    ValueError and silently fell back to the same URGENT default Days
    15-17 already fixed twice over for the prefix half of this exact
    line. Reproduced directly before the fix: this exact input logged
    "Unrecognized triage level from model: '​emergency'" and
    returned TriageLevel.URGENT, not EMERGENCY.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")
    raw = "LEVEL: ​emergency\nRATIONALE: Severe crushing chest pain radiating to the arm."

    decision = backend._parse(raw)

    assert decision.level == TriageLevel.EMERGENCY
    assert decision.rationale == "Severe crushing chest pain radiating to the arm."


def test_anthropic_backend_call_converts_empty_content_response_to_triage_backend_error(monkeypatch):
    """
    Real bug, found by auditing every third-party-API backend in this
    codebase for the same failure class the last five days' entries in
    docs/INTERVIEW_NOTES.md already fixed elsewhere: a manually-parsed
    response shape that isn't defended against raising a raw, uncaught
    exception. GroqReasoningBackend._call (app/agents/groq_backends.py)
    already wraps its own response-shape parsing in
    `except (KeyError, IndexError)`, and app/adapters/bhashini.py does
    the same in four places - but AnthropicReasoningBackend._call's
    `message.content[0].text` had no such guard. Reproduced directly
    first: `backend._client.messages.create` returning a message whose
    `.content` is an empty list makes `message.content[0]` raise a raw
    IndexError - confirmed via a Python REPL before this test or the fix
    were written. Without the fix, that IndexError is not one of the
    types propose()'s own `except (APIConnectionError, RateLimitError,
    APIStatusError)` matches, so it would propagate straight through
    run_triage_reasoning() and out of app/main.py's _run_triage (which
    only catches TriageBackendError) as a raw 500 - see
    test_assess_ordinary_case_returns_503_not_500_when_backend_returns_no_content_blocks
    in tests/test_main.py for the live-endpoint proof.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")

    class _EmptyContentMessage:
        content: list = []

    monkeypatch.setattr(backend._client.messages, "create", lambda **kwargs: _EmptyContentMessage())
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError, match="Unexpected Anthropic response shape"):
        backend._call(case)


def test_anthropic_backend_propose_converts_empty_content_response_to_triage_backend_error(monkeypatch):
    """
    Same regression as the test above, exercised through propose() - the
    method run_triage_reasoning() actually calls - not _call() in
    isolation, the same "prove it at the real call path, not just the
    helper" standard test_anthropic_backend_propose_converts_invalid_rationale_to_triage_backend_error
    above already uses.
    """
    backend = AnthropicReasoningBackend(api_key="test-key-not-used-no-network-call")

    class _EmptyContentMessage:
        content: list = []

    monkeypatch.setattr(backend._client.messages, "create", lambda **kwargs: _EmptyContentMessage())
    case = _case("mild cough for two days")

    with pytest.raises(TriageBackendError, match="Unexpected Anthropic response shape"):
        backend.propose(case)


def test_deterministic_fallback_backend_always_proposes_conservative_urgent():
    """
    DeterministicFallbackReasoningBackend (app/main.py's zero-API path
    when AnthropicReasoningBackend is unavailable or fails) must never
    guess a specific clinical level from symptom_text - it always
    proposes the same fixed URGENT/confidence=0.0 decision, regardless
    of what the case looks like, so it can never silently under-triage a
    case a real backend might have escalated further. Checked against
    two very different symptom_texts to prove it isn't secretly
    keyword-sensitive.
    """
    backend = DeterministicFallbackReasoningBackend()

    mild_case = _case("a small paper cut on my finger")
    severe_looking_case = _case("crushing chest pain radiating to my left arm")

    mild_decision = backend.propose(mild_case)
    severe_decision = backend.propose(severe_looking_case)

    assert mild_decision.level == TriageLevel.URGENT
    assert severe_decision.level == TriageLevel.URGENT
    assert mild_decision.confidence == 0.0
    assert severe_decision.confidence == 0.0
    assert "not a clinical judgment" in mild_decision.rationale


def test_deterministic_fallback_backend_never_reached_for_red_flag_cases():
    """
    run_triage_reasoning's red-flag short-circuit takes priority over
    ANY backend, including this one - proven the same way
    test_red_flag_case_short_circuits_without_calling_backend already
    proves it for a plain FakeBackend, so the fallback backend can never
    accidentally downgrade an already-detected emergency to URGENT.
    """
    case = _case("severe bleeding and unconscious", red_flags=["unconscious"])
    decision = run_triage_reasoning(case, backend=DeterministicFallbackReasoningBackend())

    assert decision.level == TriageLevel.EMERGENCY


class TestGuidelineInformedFallbackBackend:
    """
    Real users testing the live deployment (no ANTHROPIC_API_KEY/
    GROQ_API_KEY configured) reported every case producing the identical
    URGENT result. GuidelineInformedFallbackBackend replaces
    DeterministicFallbackReasoningBackend as app/main.py's actual
    zero-API fallback (DeterministicFallbackReasoningBackend itself is
    untouched and still covered by its own tests above - this is a new,
    separate class, not a modification of a safety-tested one).
    """

    @staticmethod
    def _index():
        from app.agents.verify import GuidelineIndex, load_guideline_chunks

        return GuidelineIndex(load_guideline_chunks())

    def test_proposes_the_real_guideline_level_for_a_specific_match(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("mild headache, no confusion or neck stiffness")

        decision = backend.propose(case)

        assert decision.level == TriageLevel.SELF_CARE
        assert decision.confidence == 0.0  # still not a real clinical judgment
        assert "guideline-text match" in decision.rationale

    def test_still_reaches_emergency_end_to_end_on_a_genuinely_specific_match(self):
        # propose() itself is capped at URGENT (see
        # test_never_proposes_emergency_directly_even_on_an_emergency_match
        # below) - this proves the case still genuinely reaches EMERGENCY
        # through the real pipeline, via verify_triage_decision's own
        # separate escalation check straight afterward, not that
        # capping the proposal cost this project any real recall.
        from app.agents.triage import GuidelineInformedFallbackBackend
        from app.agents.verify import verify_triage_decision

        index = self._index()
        backend = GuidelineInformedFallbackBackend(index)
        case = _case("sudden weakness on one side of my body and slurred speech")

        decision = backend.propose(case)
        assert decision.level == TriageLevel.URGENT
        assert decision.confidence == 0.0

        verified = verify_triage_decision(case, decision, index)
        assert verified.level == TriageLevel.EMERGENCY
        assert verified.guideline_evidence is not None

    def test_never_proposes_emergency_directly_even_on_an_emergency_match(self):
        # Real bug, found 16 Sep 2026: propose() used to return
        # best_match.level_hint verbatim, which can be EMERGENCY -
        # contradicting this class's own docstring ("Never a guessed
        # EMERGENCY") and, worse, silently losing the evidence for it:
        # verify_triage_decision short-circuits on
        # decision.level == EMERGENCY assuming that can only mean Entry
        # 4's red-flag path (which has no guideline_evidence to attach),
        # so a case that reached EMERGENCY straight from propose() came
        # out of /assess with guideline_evidence=null - the single
        # highest-stakes output this system produces, with zero
        # retrievable reason. Reproduced directly with real symptom text
        # that matches an EMERGENCY guideline chunk but contains no
        # literal RED_FLAG_TERMS substring, so has_red_flag is False and
        # this class's propose() is genuinely reached.
        from app.agents.triage import GuidelineInformedFallbackBackend

        index = self._index()
        backend = GuidelineInformedFallbackBackend(index)
        case = _case("sweating a lot and pain spreading to my arm and jaw")
        assert case.has_red_flag is False  # confirms this class is genuinely reached

        decision = backend.propose(case)

        assert decision.level == TriageLevel.URGENT  # never EMERGENCY straight from this class
        assert decision.confidence == 0.0

    def test_falls_back_to_conservative_urgent_on_incidental_overlap_only(self):
        # Real bug this backend must not reintroduce: "I have a fever and
        # body ache" shares only the generic word "body" with the stroke
        # guideline chunk - must not be trusted enough to propose a level
        # from that alone, same GENERIC_OVERLAP_TERMS gate
        # verify_triage_decision already uses.
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("I have a fever and body ache")

        decision = backend.propose(case)

        assert decision.level == TriageLevel.URGENT
        assert decision.confidence == 0.0
        assert "no specific guideline match" in decision.rationale

    def test_falls_back_to_conservative_urgent_when_no_match_at_all(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("qwerty zzz nonmatching gibberish text")

        decision = backend.propose(case)

        assert decision.level == TriageLevel.URGENT
        assert decision.confidence == 0.0

    def test_does_not_downgrade_a_headache_with_the_very_symptoms_it_denies(self):
        # Real bug this backend must not reintroduce: TF-IDF cosine
        # similarity is blind to negation, so "mild headache" alone
        # scores well against the guideline chunk asserting a headache
        # WITHOUT visual changes/confusion/neck stiffness can be
        # self-cared - even when the patient's own text says they HAVE
        # those exact danger signs.
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("mild headache with visual changes and confusion")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_does_not_downgrade_a_wound_that_is_still_actively_bleeding(self):
        # Double-negation trap: "has NOT stopped bleeding" negates
        # "stopped", not "bleeding" - a naive negation-cue check sees
        # "not" near "bleeding" and wrongly treats it as denied, when
        # the wound is actively bleeding.
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("scrape on my knee that has not stopped bleeding")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_does_not_downgrade_a_wound_that_looks_infected(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("cut that stopped bleeding but now looks infected")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_does_not_downgrade_nausea_with_vomiting_and_fever(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("mild nausea with vomiting and fever")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_does_not_downgrade_a_cough_with_breathlessness_and_chest_pain(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("persistent cough for a week with breathlessness and chest pain")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_does_not_downgrade_a_rapidly_spreading_rash_with_fever(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("skin rash that is spreading rapidly with fever")

        decision = backend.propose(case)

        assert decision.level != TriageLevel.SELF_CARE

    def test_still_proposes_self_care_for_a_wound_that_has_genuinely_stopped_bleeding(self):
        # Guards against a fix that's too aggressive: merely mentioning
        # "bleeding" in the context of it having stopped must not, by
        # itself, force an escalation - the exclusion is for ACTIVE
        # bleeding or infection, not the word "bleeding" appearing at all.
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        case = _case("minor cut that stopped bleeding, no signs of infection")

        decision = backend.propose(case)

        assert decision.level == TriageLevel.SELF_CARE

    def test_never_reached_for_red_flag_cases(self):
        from app.agents.triage import GuidelineInformedFallbackBackend

        case = _case("severe bleeding and unconscious", red_flags=["unconscious"])
        decision = run_triage_reasoning(case, backend=GuidelineInformedFallbackBackend(self._index()))

        assert decision.level == TriageLevel.EMERGENCY

    def test_end_to_end_differentiates_across_levels_with_zero_api_key(self):
        """
        The actual, real-world proof: run a realistic spread of ordinary
        complaints through the exact same two-stage path app/main.py's
        _run_pipeline uses when no live backend is configured (propose,
        then verify_triage_decision's own separate escalation check - a
        real patient never sees propose()'s own output in isolation, so
        neither should this test), and confirm it produces genuinely
        different levels - not the same flat URGENT for everything, which
        is the precise complaint real users reported.
        """
        from app.agents.triage import GuidelineInformedFallbackBackend
        from app.agents.verify import verify_triage_decision

        index = self._index()
        backend = GuidelineInformedFallbackBackend(index)
        cases = {
            "mild headache, no confusion or neck stiffness": TriageLevel.SELF_CARE,
            "small cut, stopped bleeding, no infection": TriageLevel.SELF_CARE,
            "persistent cough for over a week, no breathlessness": TriageLevel.CLINIC_VISIT,
            "minor skin rash, not spreading, no fever": TriageLevel.CLINIC_VISIT,
            "high fever above 39 degrees for three days with chills": TriageLevel.URGENT,
            "sudden weakness on one side of my body and slurred speech": TriageLevel.EMERGENCY,
        }
        levels_seen = set()
        for text, expected in cases.items():
            case = _case(text)
            decision = verify_triage_decision(case, backend.propose(case), index)
            assert decision.level == expected, f"{text!r} expected {expected}, got {decision.level}"
            levels_seen.add(decision.level)

        assert len(levels_seen) >= 4, "must produce genuinely different levels, not one flat default"

    def test_does_not_propose_self_care_from_a_negated_guideline_match(self):
        # Real bug, found by an adversarial output-quality review the
        # same day this class was built: "bleeding a lot, won't stop"
        # scored 0.293 (has_specific_overlap=True, shares "cut"/
        # "bleeding") against the SELF_CARE chunk describing a cut that
        # has STOPPED bleeding - word-overlap similarity has no concept
        # of negation, so an actively bleeding wound was proposed
        # SELF_CARE on the strength of a chunk describing the opposite
        # situation. _MIN_SIMILARITY_FOR_PROPOSAL=0.4 (stricter than
        # verify_triage_decision's escalation-only 0.2) closes this -
        # every genuine match in this module's own calibration set
        # scores >= 0.466, so raising the bar costs nothing there.
        from app.agents.triage import GuidelineInformedFallbackBackend

        backend = GuidelineInformedFallbackBackend(self._index())
        decision = backend.propose(_case("deep cut on my hand, bleeding a lot, won't stop"))

        assert decision.level == TriageLevel.URGENT  # the safe default, not SELF_CARE
        assert decision.confidence == 0.0

    def test_a_weak_match_the_backend_declines_still_escalates_via_verify_triage_decision(self):
        # The stricter 0.4 bar must not lose real recall: a genuine
        # stroke phrasing scoring 0.292 (below this class's own bar) no
        # longer gets a level proposed by this class directly, but must
        # still reach EMERGENCY through verify_triage_decision's
        # separate, unchanged, lower-barred (0.2) escalation check
        # moments later in the real pipeline - proven end to end, not
        # just asserted in isolation.
        from app.agents.triage import GuidelineInformedFallbackBackend
        from app.agents.verify import verify_triage_decision

        index = self._index()
        backend = GuidelineInformedFallbackBackend(index)
        case = _case("my face feels droopy on one side and my speech sounds strange")

        decision = backend.propose(case)
        assert decision.level == TriageLevel.URGENT  # declined to propose from a sub-0.4 match

        verified = verify_triage_decision(case, decision, index)
        assert verified.level == TriageLevel.EMERGENCY  # but the safety net still catches it
