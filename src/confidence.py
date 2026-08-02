"""
Deterministic confidence scoring for recommendation output.

Quantifies how certain the system should be in its own recommendations,
computed entirely from signals already produced by the existing scoring/NL
pipeline - never an LLM self-report, which is poorly calibrated for
self-assessed certainty. Two entry points:

- score_confidence(): the deterministic recommend_songs() path.
- score_nl_confidence(): the Gemini-backed run_nl_query() path, which reuses
  score_confidence() as its base signal and layers on NL-pipeline-specific
  ones (how usable the extracted energy value was, whether grounding notes
  were found).

Both are additive - callers invoke them alongside recommend_songs()/
run_nl_query() rather than folding a new field into either function's
existing return shape, since recommend_songs()'s 3-tuple return is already
hard-destructured by src/main.py and src/streamlit_app.py.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.recommender import ACOUSTIC_WEIGHT, ENERGY_WEIGHT, GENRE_WEIGHT, MOOD_WEIGHT, score_breakdown

CATEGORICAL_WEIGHT = 0.6
TOP1_WEIGHT = 0.4

DET_WEIGHT = 0.55
ENERGY_CONF_WEIGHT = 0.25
GROUNDING_WEIGHT = 0.20

HIGH_THRESHOLD = 0.75
MEDIUM_THRESHOLD = 0.4

# run_nl_query() statuses where the NL layer already degraded to the
# deterministic fallback table - confidence is reported as a flat, low
# sentinel rather than blended with the deterministic score, since these
# statuses already encode a specific, different kind of failure (API error
# vs. a hallucination catch) that a single blended number would obscure.
DEGRADED_STATUSES = {"extraction_failed", "explanation_failed", "guardrail_tripped"}


@dataclass
class ConfidenceResult:
    score: float
    tier: str  # "low" | "medium" | "high" | "n/a"
    signals: Dict[str, float]
    reason: str


def _tier_for(raw: float) -> str:
    if raw >= HIGH_THRESHOLD:
        return "high"
    if raw >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def score_confidence(
    user_prefs: Dict, recommendations: List[Tuple[Dict, float, str]]
) -> ConfidenceResult:
    """Confidence for the deterministic recommend_songs() path.

    Blends two signals:
    - categorical_coverage: how often the top-k actually match the genre/mood
      the user specified (fields they didn't specify are vacuously satisfied,
      so a pure-energy query isn't penalized for a preference it never made).
    - top1_normalized: the #1 result's score as a fraction of the true
      achievable ceiling for this profile.

    Uses score_breakdown() directly rather than parsing the joined reasons
    string, since the energy-closeness reason fires by near-chance on a dense
    catalog and would mask a genuine genre/mood miss.
    """
    if not recommendations:
        return ConfidenceResult(
            score=0.0,
            tier="n/a",
            signals={},
            reason="No recommendations were returned, so confidence is undefined.",
        )

    fav_genre = user_prefs["genre"]
    fav_mood = user_prefs["mood"]
    likes_acoustic = user_prefs.get("likes_acoustic")

    specified_fields = []
    if fav_genre:
        specified_fields.append("genre")
    if fav_mood:
        specified_fields.append("mood")

    if specified_fields:
        per_song_coverage = []
        for song, _score, _reasons in recommendations:
            breakdown = score_breakdown(user_prefs, song)
            matched = sum(1 for field in specified_fields if breakdown.get(field, 0) > 0)
            per_song_coverage.append(matched / len(specified_fields))
        categorical_coverage = sum(per_song_coverage) / len(per_song_coverage)
    else:
        categorical_coverage = 1.0

    ceiling = GENRE_WEIGHT + MOOD_WEIGHT + ENERGY_WEIGHT + (ACOUSTIC_WEIGHT if likes_acoustic is not None else 0.0)
    top1_score = recommendations[0][1]
    top1_normalized = max(0.0, min(1.0, top1_score / ceiling))

    raw = CATEGORICAL_WEIGHT * categorical_coverage + TOP1_WEIGHT * top1_normalized
    tier = _tier_for(raw)

    if not specified_fields:
        reason = (
            "No genre/mood preference was specified, so confidence reflects only "
            "how closely the top match fits the requested energy/acoustic profile."
        )
    elif categorical_coverage >= 0.99:
        reason = "The recommended songs match your specified genre/mood preferences well."
    elif categorical_coverage > 0:
        reason = (
            "Some recommendations match your specified genre/mood preferences; "
            "others are the closest available fallback."
        )
    else:
        reason = (
            "None of the recommendations match your specified genre/mood preferences; "
            "results are the closest available fallback based on energy/acoustic fit alone."
        )

    return ConfidenceResult(
        score=raw,
        tier=tier,
        signals={"categorical_coverage": categorical_coverage, "top1_normalized": top1_normalized},
        reason=reason,
    )


def score_nl_confidence(
    status: str,
    user_prefs: Dict,
    recommendations: List[Tuple[Dict, float, str]],
    raw_profile: Optional[Dict] = None,
    grounding_notes: Optional[List[str]] = None,
) -> ConfidenceResult:
    """Confidence for the Gemini-backed run_nl_query() path.

    Degraded statuses (extraction/explanation failure, guardrail trip) always
    report a flat low sentinel - status/message already distinguish the
    failure kind, so blending would only lose information.

    On "ok", blends the deterministic score with two NL-specific signals:
    how usable the extracted energy value was before clamp_profile() touched
    it, and whether the grounding corpus had any notes for this
    recommendation set.
    """
    if status in DEGRADED_STATUSES:
        return ConfidenceResult(
            score=0.0,
            tier="low",
            signals={},
            reason=f"The natural-language layer degraded ({status}); recommendations fell back to the deterministic table.",
        )

    deterministic_result = score_confidence(user_prefs, recommendations)

    raw_energy = (raw_profile or {}).get("energy")
    try:
        parsed_energy = float(raw_energy)
    except (TypeError, ValueError):
        energy_confidence = 0.0
    else:
        energy_confidence = 1.0 if 0.0 <= parsed_energy <= 1.0 else 0.4

    grounding_coverage = 1.0 if grounding_notes else 0.5

    raw = (
        DET_WEIGHT * deterministic_result.score
        + ENERGY_CONF_WEIGHT * energy_confidence
        + GROUNDING_WEIGHT * grounding_coverage
    )
    tier = _tier_for(raw)

    reason = (
        f"Confidence reflects catalog match quality ({deterministic_result.tier}), "
        f"how directly the extracted energy value could be used ({energy_confidence:.2f}), "
        f"and whether grounding notes were available ({'yes' if grounding_notes else 'no'})."
    )

    return ConfidenceResult(
        score=raw,
        tier=tier,
        signals={
            "deterministic": deterministic_result.score,
            "energy_confidence": energy_confidence,
            "grounding_coverage": grounding_coverage,
        },
        reason=reason,
    )
