from app.agents.verify import GuidelineChunk, GuidelineIndex, load_guideline_chunks, verify_triage_decision
from app.schemas import CaseSummary, TriageDecision, TriageLevel


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


def test_guideline_index_top_matches_ranks_by_relevance():
    chunks = [
        GuidelineChunk(source="a", level_hint=TriageLevel.SELF_CARE, text="mild headache rest fluids"),
        GuidelineChunk(source="b", level_hint=TriageLevel.EMERGENCY, text="chest pain breathlessness sweating"),
    ]
    index = GuidelineIndex(chunks)

    top = index.top_matches("severe chest pain and breathlessness", k=1)

    assert len(top) == 1
    assert top[0].source == "b"
