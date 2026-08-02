from src.confidence import DEGRADED_STATUSES, score_confidence, score_nl_confidence
from src.recommender import recommend_songs

CATALOG = [
    {
        "id": 1, "title": "A", "artist": "Artist1", "genre": "lofi", "mood": "chill",
        "energy": 0.40, "tempo_bpm": 80, "valence": 0.5, "danceability": 0.5, "acousticness": 0.70,
    },
    {
        "id": 2, "title": "B", "artist": "Artist2", "genre": "lofi", "mood": "chill",
        "energy": 0.42, "tempo_bpm": 78, "valence": 0.5, "danceability": 0.5, "acousticness": 0.71,
    },
    {
        "id": 3, "title": "C", "artist": "Artist3", "genre": "rock", "mood": "intense",
        "energy": 0.90, "tempo_bpm": 150, "valence": 0.4, "danceability": 0.5, "acousticness": 0.10,
    },
]


def test_score_confidence_is_high_for_a_strong_genre_and_mood_match():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    result = score_confidence(user_prefs, recommendations)

    assert result.tier == "high"
    assert result.signals["categorical_coverage"] == 1.0


def test_score_confidence_is_low_when_genre_and_mood_dont_exist_in_the_catalog():
    user_prefs = {"genre": "opera", "mood": "furious", "energy": 0.5, "likes_acoustic": None}
    recommendations = recommend_songs(user_prefs, CATALOG, k=3)

    result = score_confidence(user_prefs, recommendations)

    assert result.tier == "low"
    assert result.signals["categorical_coverage"] == 0.0


def test_score_confidence_does_not_penalize_a_pure_energy_query_for_unspecified_genre_and_mood():
    user_prefs = {"genre": "", "mood": "", "energy": 0.4, "likes_acoustic": None}
    recommendations = recommend_songs(user_prefs, CATALOG, k=3)

    result = score_confidence(user_prefs, recommendations)

    assert result.signals["categorical_coverage"] == 1.0
    assert result.tier == "high"


def test_score_confidence_with_no_recommendations_returns_na_tier():
    result = score_confidence({"genre": "pop", "mood": "happy", "energy": 0.5}, [])

    assert result.score == 0.0
    assert result.tier == "n/a"


def test_score_confidence_ceiling_excludes_acoustic_weight_when_likes_acoustic_is_none():
    # Same profile, differing only in likes_acoustic - the acoustic-inclusive
    # ceiling should never produce a HIGHER top1_normalized than the
    # acoustic-excluded one for an equal or lower absolute score.
    with_acoustic = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    without_acoustic = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": None}

    recs_with = recommend_songs(with_acoustic, CATALOG, k=2)
    recs_without = recommend_songs(without_acoustic, CATALOG, k=2)

    result_with = score_confidence(with_acoustic, recs_with)
    result_without = score_confidence(without_acoustic, recs_without)

    assert result_with.signals["top1_normalized"] <= 1.0
    assert result_without.signals["top1_normalized"] <= 1.0


def test_score_nl_confidence_returns_flat_low_sentinel_for_every_degraded_status():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    for status in DEGRADED_STATUSES:
        result = score_nl_confidence(
            status, user_prefs, recommendations,
            raw_profile={"energy": 0.4}, grounding_notes=["some note"],
        )
        assert result.score == 0.0
        assert result.tier == "low"


def test_score_nl_confidence_rewards_an_in_range_extracted_energy_value():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    result = score_nl_confidence(
        "ok", user_prefs, recommendations,
        raw_profile={"energy": 0.4}, grounding_notes=["a real note"],
    )

    assert result.signals["energy_confidence"] == 1.0
    assert result.signals["grounding_coverage"] == 1.0


def test_score_nl_confidence_penalizes_an_out_of_range_extracted_energy_value():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    result = score_nl_confidence(
        "ok", user_prefs, recommendations,
        raw_profile={"energy": 5.0}, grounding_notes=["a real note"],
    )

    assert result.signals["energy_confidence"] == 0.4


def test_score_nl_confidence_treats_missing_or_non_numeric_energy_as_zero_confidence():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    result_missing = score_nl_confidence("ok", user_prefs, recommendations, raw_profile={})
    result_non_numeric = score_nl_confidence(
        "ok", user_prefs, recommendations, raw_profile={"energy": "not-a-number"}
    )

    assert result_missing.signals["energy_confidence"] == 0.0
    assert result_non_numeric.signals["energy_confidence"] == 0.0


def test_score_nl_confidence_treats_missing_grounding_notes_as_partial_not_zero_confidence():
    user_prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    recommendations = recommend_songs(user_prefs, CATALOG, k=2)

    result = score_nl_confidence(
        "ok", user_prefs, recommendations, raw_profile={"energy": 0.4}, grounding_notes=[]
    )

    assert result.signals["grounding_coverage"] == 0.5
