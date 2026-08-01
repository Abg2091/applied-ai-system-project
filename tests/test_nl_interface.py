import json

import anthropic
import httpx

from src.nl_interface import (
    MAX_QUERY_LENGTH,
    build_explanation_schema,
    build_extraction_schema,
    clamp_profile,
    format_candidates_for_prompt,
    format_fallback_table,
    get_catalog_vocabulary,
    has_api_key,
    run_nl_query,
    validate_query_length,
)


class FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeBlock(text)]


class FakeMessages:
    def __init__(self, responses):
        # Each entry is either a JSON response string (success) or an
        # Exception instance to raise - lets one fake client simulate a
        # Claude API failure on a specific call in the sequence.
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return FakeResponse(item)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


SMALL_CATALOG = [
    {
        "id": 1, "title": "Sunrise City", "artist": "Neon Echo", "genre": "pop", "mood": "happy",
        "energy": 0.82, "tempo_bpm": 118, "valence": 0.84, "danceability": 0.79, "acousticness": 0.18,
    },
    {
        "id": 2, "title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi", "mood": "chill",
        "energy": 0.42, "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71,
    },
]


def make_connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


def make_small_catalog() -> list:
    return [
        {"id": 1, "title": "Sunrise City", "artist": "Neon Echo", "genre": "pop", "mood": "happy"},
        {"id": 2, "title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi", "mood": "chill"},
        {"id": 3, "title": "Library Rain", "artist": "Paper Lanterns", "genre": "lofi", "mood": "chill"},
    ]


def test_get_catalog_vocabulary_returns_sorted_distinct_values():
    genres, moods = get_catalog_vocabulary(make_small_catalog())

    assert genres == ["lofi", "pop"]
    assert moods == ["chill", "happy"]


def test_build_extraction_schema_constrains_genre_and_mood_to_catalog_plus_unspecified():
    schema = build_extraction_schema(["pop", "lofi"], ["happy", "chill"])

    assert schema["properties"]["genre"]["enum"] == ["lofi", "pop", "unspecified"]
    assert schema["properties"]["mood"]["enum"] == ["chill", "happy", "unspecified"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"genre", "mood", "energy", "likes_acoustic"}


def test_clamp_profile_leaves_in_range_energy_unchanged():
    profile = {"genre": "pop", "mood": "happy", "energy": 0.6, "likes_acoustic": True}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 0.6
    assert clamped["genre"] == "pop"


def test_clamp_profile_clamps_above_range_energy():
    profile = {"genre": "pop", "mood": "happy", "energy": 5.0, "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 1.0


def test_clamp_profile_clamps_below_range_energy():
    profile = {"genre": "pop", "mood": "happy", "energy": -3.2, "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 0.0


def test_clamp_profile_falls_back_to_neutral_energy_on_non_numeric_value():
    profile = {"genre": "pop", "mood": "happy", "energy": "not-a-number", "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 0.5


def test_clamp_profile_falls_back_to_neutral_energy_when_missing():
    profile = {"genre": "pop", "mood": "happy", "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 0.5


def test_clamp_profile_maps_unspecified_sentinel_to_empty_string():
    profile = {"genre": "unspecified", "mood": "unspecified", "energy": 0.5, "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["genre"] == ""
    assert clamped["mood"] == ""


def test_validate_query_length_returns_valid_text_unchanged():
    text = "chill songs for studying"

    assert validate_query_length(text) == text


def test_validate_query_length_accepts_text_at_exact_limit():
    text = "a" * MAX_QUERY_LENGTH

    assert validate_query_length(text) == text


def test_validate_query_length_rejects_empty_text():
    try:
        validate_query_length("")
        assert False, "expected ValueError for empty text"
    except ValueError:
        pass


def test_validate_query_length_rejects_whitespace_only_text():
    try:
        validate_query_length("    ")
        assert False, "expected ValueError for whitespace-only text"
    except ValueError:
        pass


def test_validate_query_length_rejects_overlong_text():
    try:
        validate_query_length("a" * (MAX_QUERY_LENGTH + 1))
        assert False, "expected ValueError for overlong text"
    except ValueError:
        pass


def test_build_explanation_schema_constrains_song_id_enum_to_candidate_ids():
    schema = build_explanation_schema([2, 5, 9])

    song_id_schema = schema["properties"]["song_notes"]["items"]["properties"]["song_id"]
    assert song_id_schema["enum"] == [2, 5, 9]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["song_notes"]["items"]["additionalProperties"] is False


def test_format_candidates_for_prompt_includes_recommended_songs_and_notes():
    recommendations = [
        ({"id": 1, "title": "A", "artist": "X", "genre": "pop", "mood": "happy"}, 3.5, "genre matches"),
    ]

    text = format_candidates_for_prompt({"genre": "pop"}, recommendations, ["Pop is upbeat."])

    assert "id=1" in text
    assert "Pop is upbeat." in text
    assert "(no additional notes)" not in text


def test_format_candidates_for_prompt_notes_absence_of_grounding_explicitly():
    text = format_candidates_for_prompt({"genre": "pop"}, [], [])

    assert "(no additional notes)" in text


def test_run_nl_query_wires_extraction_recommendation_and_explanation_together():
    songs = [
        {
            "id": 1, "title": "Sunrise City", "artist": "Neon Echo", "genre": "pop", "mood": "happy",
            "energy": 0.82, "tempo_bpm": 118, "valence": 0.84, "danceability": 0.79, "acousticness": 0.18,
        },
        {
            "id": 2, "title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi", "mood": "chill",
            "energy": 0.42, "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71,
        },
    ]
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    explanation_response = json.dumps(
        {
            "summary": "These fit your chill lofi mood.",
            "song_notes": [{"song_id": 2, "note": "matches genre and mood"}],
        }
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(songs, "chill lofi songs", client)

    assert result["user_prefs"]["genre"] == "lofi"
    assert result["recommendations"][0][0]["id"] == 2
    assert result["explanation"]["summary"] == "These fit your chill lofi mood."

    # The explanation call's schema must be built from the ACTUAL recommended
    # IDs, not a hardcoded/catalog-wide set - this is the structural
    # anti-hallucination guardrail, so verify it end to end here.
    recommended_ids = {song["id"] for song, _, _ in result["recommendations"]}
    explanation_call = client.messages.calls[1]
    song_id_enum = explanation_call["output_config"]["format"]["schema"]["properties"][
        "song_notes"
    ]["items"]["properties"]["song_id"]["enum"]
    assert set(song_id_enum) == recommended_ids


def test_has_api_key_true_when_env_var_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")

    assert has_api_key() is True


def test_has_api_key_false_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert has_api_key() is False


def test_format_fallback_table_includes_song_titles_artists_and_scores():
    recommendations = [
        ({"id": 1, "title": "Sunrise City", "artist": "Neon Echo"}, 4.25, "genre matches"),
    ]

    table = format_fallback_table({"genre": "pop", "mood": "happy"}, recommendations)

    assert "Sunrise City" in table
    assert "Neon Echo" in table
    assert "4.25" in table


def test_run_nl_query_falls_back_to_default_profile_when_extraction_fails():
    client = FakeClient([make_connection_error()])

    result = run_nl_query(SMALL_CATALOG, "chill lofi songs", client)

    assert result["status"] == "extraction_failed"
    assert result["user_prefs"]["genre"] == "lofi"  # DEFAULT_FALLBACK_PROFILE
    assert result["explanation"] is None
    assert result["fallback_table"] is not None
    assert len(result["recommendations"]) > 0
    # Only one call was attempted (extraction) - the explanation call never happens.
    assert len(client.messages.calls) == 1


def test_run_nl_query_falls_back_to_table_when_explanation_fails():
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    client = FakeClient([profile_response, make_connection_error()])

    result = run_nl_query(SMALL_CATALOG, "chill lofi songs", client)

    assert result["status"] == "explanation_failed"
    assert result["user_prefs"]["genre"] == "lofi"
    assert result["recommendations"][0][0]["id"] == 2  # LoRoom, the real (non-default) match
    assert result["explanation"] is None
    assert "LoRoom" in result["fallback_table"]


def test_run_nl_query_includes_real_grounding_notes_for_recommended_genre_and_artist():
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    explanation_response = json.dumps(
        {"summary": "ok", "song_notes": [{"song_id": 2, "note": "matches"}]}
    )
    client = FakeClient([profile_response, explanation_response])

    run_nl_query(SMALL_CATALOG, "chill lofi songs", client)

    explanation_call = client.messages.calls[1]
    user_content = explanation_call["messages"][0]["content"]
    # Substrings unique to data/knowledge/genre_notes.json's "lofi" entry and
    # artist_notes.json's "LoRoom" entry - confirms the real on-disk corpus,
    # not just a hardcoded stub, made it into the prompt.
    assert "background listening" in user_content
    assert "mellow lo-fi pieces" in user_content


SIX_SONG_CATALOG = [
    {
        "id": 1, "title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi", "mood": "chill",
        "energy": 0.42, "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71,
    },
    {
        "id": 2, "title": "Library Rain", "artist": "Paper Lanterns", "genre": "lofi", "mood": "chill",
        "energy": 0.35, "tempo_bpm": 72, "valence": 0.60, "danceability": 0.58, "acousticness": 0.86,
    },
    {
        "id": 3, "title": "Focus Flow", "artist": "LoRoom", "genre": "lofi", "mood": "focused",
        "energy": 0.40, "tempo_bpm": 80, "valence": 0.59, "danceability": 0.60, "acousticness": 0.78,
    },
    {
        "id": 4, "title": "Spacewalk Thoughts", "artist": "Orbit Bloom", "genre": "ambient", "mood": "chill",
        "energy": 0.28, "tempo_bpm": 60, "valence": 0.65, "danceability": 0.41, "acousticness": 0.92,
    },
    {
        "id": 5, "title": "Half Light", "artist": "Sable Lane", "genre": "indie pop", "mood": "relaxed",
        "energy": 0.48, "tempo_bpm": 92, "valence": 0.60, "danceability": 0.55, "acousticness": 0.50,
    },
    {
        # Deliberately the worst match for a lofi/chill/energy=0.4 query, so
        # it's the one song excluded from the top-5 recommendations below.
        "id": 6, "title": "Iron Verdict", "artist": "Grave Circuit", "genre": "metal", "mood": "aggressive",
        "energy": 0.97, "tempo_bpm": 170, "valence": 0.30, "danceability": 0.35, "acousticness": 0.03,
    },
]


def test_run_nl_query_trips_guardrail_when_explanation_mentions_an_unrecommended_catalog_song():
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    # "Iron Verdict" is a real catalog song but scores far too low to be
    # recommended for this profile (see SIX_SONG_CATALOG's comment) - so
    # naming it in the explanation is exactly the scope-creep check_grounding
    # exists to catch.
    explanation_response = json.dumps(
        {
            "summary": "If you want something different, Iron Verdict brings a lot of energy!",
            "song_notes": [{"song_id": 1, "note": "matches your mood"}],
        }
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(SIX_SONG_CATALOG, "chill lofi songs", client)

    assert result["status"] == "guardrail_tripped"
    assert result["explanation"] is None
    assert result["fallback_table"] is not None
    assert all(song["id"] != 6 for song, _, _ in result["recommendations"])


def test_run_nl_query_status_ok_on_full_success():
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    explanation_response = json.dumps(
        {"summary": "Great chill picks.", "song_notes": [{"song_id": 2, "note": "matches"}]}
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(SMALL_CATALOG, "chill lofi songs", client)

    assert result["status"] == "ok"
    assert result["message"] is None
    assert result["fallback_table"] is None
    assert result["explanation"]["summary"] == "Great chill picks."
