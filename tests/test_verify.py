from app.agents.verify import (
    GuidelineChunk,
    GuidelineIndex,
    load_guideline_chunks,
    verify_triage_decision,
)
from app.schemas import CaseSummary, GuidelineEvidence, TriageDecision, TriageLevel


def _case(text: str) -> CaseSummary:
    return CaseSummary(symptom_text=text, age=30, duration_days=1, has_image=False, red_flag_terms=[])


def _decision(level: TriageLevel, confidence: float = 0.7) -> TriageDecision:
    return TriageDecision(level=level, rationale="model rationale", confidence=confidence)


def test_load_guideline_chunks_reads_the_bundled_seed_corpus():
    chunks = load_guideline_chunks()
    assert len(chunks) >= 10
    assert all(isinstance(c, GuidelineChunk) for c in chunks)
    assert {c.level_hint for c in chunks} == {
        TriageLevel.SELF_CARE,
        TriageLevel.CLINIC_VISIT,
        TriageLevel.URGENT,
        TriageLevel.EMERGENCY,
    }


def test_verify_escalates_when_guideline_implies_higher_severity():
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("chest pain with sweating and pain going down my arm")
    proposed = _decision(TriageLevel.CLINIC_VISIT)  # model under-called it

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.EMERGENCY
    assert "chest pain" in verified.rationale.lower()
    assert "STARTER_SEED" in verified.rationale


def test_verify_attaches_real_guideline_evidence_when_escalating():
    """
    Added 13 Sep 2026 alongside GuidelineEvidence itself: a physician
    seeing the escalated level must also see WHY - the actual guideline
    text and a real, checkable similarity score, not just the fact that
    an escalation happened.
    """
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("chest pain with sweating and pain going down my arm")
    proposed = _decision(TriageLevel.CLINIC_VISIT)

    verified = verify_triage_decision(case, proposed, index)

    evidence = verified.guideline_evidence
    assert isinstance(evidence, GuidelineEvidence)
    assert evidence.matched_level == TriageLevel.EMERGENCY
    assert "chest pain" in evidence.matched_text.lower()
    assert 0.5 < evidence.similarity <= 1.0  # a genuinely strong match, per this module's own docstring


def test_verify_attaches_guideline_evidence_even_without_escalating():
    """
    The far more common case: no escalation needed, but the evidence
    behind that "no escalation needed" call must still be visible -
    previously this was computed internally then thrown away the
    instant it didn't trigger an escalation.
    """
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("mild headache, no visual changes or confusion")
    proposed = _decision(TriageLevel.SELF_CARE)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.SELF_CARE
    assert verified.guideline_evidence is not None
    assert verified.guideline_evidence.matched_level == TriageLevel.SELF_CARE


def test_verify_attaches_no_evidence_for_an_already_emergency_decision():
    """
    An EMERGENCY proposal short-circuits before any guideline lookup
    happens at all (nothing above EMERGENCY to escalate to) - evidence
    must be honestly absent here, not fabricated, since this decision
    was never actually checked against the index. See
    schemas.GuidelineEvidence's own docstring for why that distinction
    matters.
    """
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("severe bleeding that won't stop")
    proposed = _decision(TriageLevel.EMERGENCY)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.guideline_evidence is None


def test_best_match_with_score_returns_a_real_similarity_score():
    index = GuidelineIndex(load_guideline_chunks())

    result = index.best_match_with_score("chest pain with sweating and pain going down my arm")

    assert result is not None
    chunk, score = result
    assert chunk.level_hint == TriageLevel.EMERGENCY
    assert isinstance(score, float)
    assert 0.5 < score <= 1.0


def test_best_match_with_score_returns_none_below_threshold():
    index = GuidelineIndex(load_guideline_chunks())

    result = index.best_match_with_score("qwerty zzz nonmatching gibberish text")

    assert result is None


def test_verify_leaves_correctly_matched_level_unchanged():
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("mild headache, no visual changes or confusion")
    proposed = _decision(TriageLevel.SELF_CARE)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.SELF_CARE
    assert verified.rationale == "model rationale"  # untouched - no escalation happened


def test_verify_never_deescalates_even_with_a_mild_top_match():
    # The Triage-Reasoning Agent proposed EMERGENCY (e.g. from its own
    # judgment on symptoms not in the seed corpus). Even if retrieval
    # only turns up a mild-sounding match, verification must not lower
    # the level - that's the asymmetry the docstring promises, proven
    # here rather than only claimed.
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("mild headache")
    proposed = _decision(TriageLevel.EMERGENCY)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.EMERGENCY
    assert verified is proposed  # short-circuited immediately, index never even queried


def test_verify_keeps_proposal_when_no_guideline_matches():
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("qwerty zzz nonmatching gibberish text")
    proposed = _decision(TriageLevel.CLINIC_VISIT)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.CLINIC_VISIT


def test_guideline_index_rejects_empty_corpus():
    import pytest

    with pytest.raises(ValueError):
        GuidelineIndex([])


def test_top_matches_filters_out_weak_incidental_overlap():
    # Regression test for a real bug: "mild headache" was incorrectly
    # escalated to clinic_visit because a clinic_visit chunk about fever
    # shared only the single word "mild" (cosine similarity ~0.10) and
    # was still being counted as a valid match at k=3 with no threshold.
    index = GuidelineIndex(load_guideline_chunks())

    matches = index.top_matches("mild headache, no visual changes or confusion", k=3)

    assert len(matches) == 1
    assert matches[0].level_hint == TriageLevel.SELF_CARE


def test_verify_does_not_escalate_on_a_weak_secondary_match_that_shares_only_generic_words():
    # Regression test for a real bug: "my knee pain is very mild and
    # only when climbing stairs" scores 0.340 (top-1) against a
    # SELF_CARE nausea/abdominal-pain chunk (sharing only "pain"/
    # "mild"), but an EMERGENCY chest-pain chunk was still the second-
    # ranked match at 0.301, comfortably above min_similarity=0.2.
    # Considering any of the top-3 matches (the pre-fix behavior) let
    # that weaker, less relevant EMERGENCY match override the correct,
    # stronger, less severe top-1 result - an ordinary mild knee
    # complaint must never be escalated to EMERGENCY on "pain" alone.
    index = GuidelineIndex(load_guideline_chunks())
    case = _case("my knee pain is very mild and only when climbing stairs")
    proposed = _decision(TriageLevel.URGENT)

    verified = verify_triage_decision(case, proposed, index)

    assert verified.level == TriageLevel.URGENT
    assert verified.rationale == "model rationale"  # untouched - no escalation happened
    # Real evidence is still attached even though nothing escalated
    # (added 13 Sep 2026) - this is exactly why `verified is proposed`
    # no longer holds here: a genuinely new object carrying the real
    # top-1 match, not a no-op passthrough. The top-1 match is the
    # SELF_CARE nausea chunk, not the weaker EMERGENCY chest-pain chunk
    # this test's whole point is that verification must ignore.
    assert verified.guideline_evidence is not None
    assert verified.guideline_evidence.matched_level == TriageLevel.SELF_CARE


def test_verify_does_not_escalate_on_a_single_incidental_shared_word():
    # Real bug, found 14 Sep 2026 by testing ordinary complaints against
    # the live pipeline, reported independently by real users as "every
    # input gives the same emergency/see-a-doctor output": min_similarity
    # alone let a single shared common word (not a clinical relationship)
    # push a correct SELF_CARE decision all the way to EMERGENCY. Each
    # case here shares exactly one word with the EMERGENCY chunk it used
    # to falsely match - "body" (stroke chunk), "pain" (chest-pain
    # chunk), "heavy" (bleeding chunk) - confirmed via GuidelineIndex's
    # own _shared_term_count before this fix landed.
    index = GuidelineIndex(load_guideline_chunks())
    cases = [
        "I have a fever and body ache",
        "joint pain in my knee when walking",
        "back pain from lifting something heavy",
    ]
    for text in cases:
        case = _case(text)
        proposed = _decision(TriageLevel.SELF_CARE, confidence=0.9)
        verified = verify_triage_decision(case, proposed, index)
        assert verified.level == TriageLevel.SELF_CARE, (
            f"{text!r} was wrongly escalated to {verified.level} on incidental word overlap"
        )


def test_verify_still_escalates_on_a_genuinely_strong_match():
    # The fix above must not just raise the bar until nothing matches -
    # a real emergency phrasing sharing several clinically relevant
    # words with its guideline chunk must still escalate exactly as
    # before.
    index = GuidelineIndex(load_guideline_chunks())
    for text in [
        "sudden weakness on one side of my body and slurred speech",
        "heavy bleeding from a wound that will not stop",
    ]:
        case = _case(text)
        proposed = _decision(TriageLevel.SELF_CARE, confidence=0.9)
        verified = verify_triage_decision(case, proposed, index)
        assert verified.level == TriageLevel.EMERGENCY, f"{text!r} should still escalate"


def test_guideline_index_top_matches_ranks_by_relevance():
    chunks = [
        GuidelineChunk(source="a", level_hint=TriageLevel.SELF_CARE, text="mild headache rest fluids"),
        GuidelineChunk(source="b", level_hint=TriageLevel.EMERGENCY, text="chest pain breathlessness sweating"),
    ]
    index = GuidelineIndex(chunks)

    top = index.top_matches("severe chest pain and breathlessness", k=1)

    assert len(top) == 1
    assert top[0].source == "b"
