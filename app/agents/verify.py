"""
Guideline-Verification Agent.

Checks the Triage-Reasoning Agent's proposed level against a corpus of
guideline text instead of trusting the LLM's judgment on its own. See
docs/INTERVIEW_NOTES.md, Entry 6, for why retrieval is asymmetric -
it can only escalate a proposed level, never lower one.

The bundled corpus (data/guidelines/seed_guidelines.json) is a starter
set written for this repo, not a verified extract from an official
ICMR/WHO document - see the README before treating this as production
medical content.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas import CaseSummary, TriageDecision, TriageLevel

logger = logging.getLogger(__name__)

DEFAULT_GUIDELINES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "guidelines" / "seed_guidelines.json"
)

# Ordering encodes severity rank - used to decide whether a retrieved
# guideline chunk implies a MORE cautious level than what was proposed.
_LEVEL_RANK: dict[TriageLevel, int] = {
    TriageLevel.SELF_CARE: 0,
    TriageLevel.CLINIC_VISIT: 1,
    TriageLevel.URGENT: 2,
    TriageLevel.EMERGENCY: 3,
}


@dataclass(frozen=True)
class GuidelineChunk:
    source: str
    level_hint: TriageLevel
    text: str


def load_guideline_chunks(path: Path = DEFAULT_GUIDELINES_PATH) -> list[GuidelineChunk]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        GuidelineChunk(
            source=entry["source"],
            level_hint=TriageLevel(entry["level_hint"]),
            text=entry["text"],
        )
        for entry in raw
    ]


class GuidelineIndex:
    """
    TF-IDF retrieval over the guideline corpus - not dense embeddings.

    Deliberate choice, not a shortcut: the corpus is a few dozen short,
    domain-specific chunks, where exact and near-exact medical-term
    overlap ("chest pain", "slurred speech") is already a strong signal.
    A transformer embedding model would add a heavy dependency and real
    latency for a retrieval problem this size gains little from. This
    stops being the right call once the corpus grows into the hundreds
    of documents or needs to match paraphrased, non-overlapping wording
    - at that point, swap in sentence-transformers + FAISS.
    """

    def __init__(self, chunks: list[GuidelineChunk]) -> None:
        if not chunks:
            raise ValueError("GuidelineIndex requires at least one guideline chunk.")
        self._chunks = chunks
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform([chunk.text for chunk in chunks])

    def top_matches(self, query: str, k: int = 3, min_similarity: float = 0.2) -> list[GuidelineChunk]:
        """
        min_similarity=0.2 is a real, measured threshold, not a guess:
        a genuinely relevant chunk in this corpus scores ~0.6-0.7
        cosine similarity; a chunk that only shares one incidental word
        (e.g. "mild") with the query scores ~0.09-0.10. 0.2 sits cleanly
        between those two clusters - verified in
        test_top_matches_filters_out_weak_incidental_overlap, not just
        asserted here.
        """
        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix)[0]
        ranked_indices = sorted(range(len(self._chunks)), key=lambda i: scores[i], reverse=True)
        return [self._chunks[i] for i in ranked_indices[:k] if scores[i] >= min_similarity]


def verify_triage_decision(case: CaseSummary, decision: TriageDecision, index: GuidelineIndex) -> TriageDecision:
    """
    Escalates the proposed level if a retrieved guideline chunk implies
    something more severe. Never de-escalates based on retrieval -
    de-escalating on an imperfect keyword match is a far worse failure
    mode than staying cautious, so this function is asymmetric on
    purpose. Proven, not just claimed, in
    test_verify_never_deescalates_even_with_a_mild_top_match.
    """
    if decision.level == TriageLevel.EMERGENCY:
        # Entry 4's short-circuit already reached the ceiling without a
        # model call - nothing above EMERGENCY to escalate to.
        return decision

    matches = index.top_matches(case.symptom_text, k=3)
    if not matches:
        logger.warning("No guideline match for case text - keeping the Triage-Reasoning Agent's proposal as-is.")
        return decision

    most_severe = max(matches, key=lambda chunk: _LEVEL_RANK[chunk.level_hint])

    if _LEVEL_RANK[most_severe.level_hint] > _LEVEL_RANK[decision.level]:
        return TriageDecision(
            level=most_severe.level_hint,
            rationale=(
                f"{decision.rationale} Escalated on guideline match: "
                f'"{most_severe.text}" ({most_severe.source}).'
            ),
            confidence=decision.confidence,
        )

    return decision
