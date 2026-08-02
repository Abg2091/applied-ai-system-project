import json

from google.genai import errors as genai_errors

from src.nl_interface import (
    MAX_QUERY_LENGTH,
    build_explanation_schema,
    build_extraction_schema,
    clamp_profile,
    format_candidates_for_prompt,
    format_fallback_table,
    get_catalog_artists,
    get_catalog_vocabulary,
    has_api_key,
    run_nl_query,
    run_session_demo,
    validate_query_length,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, responses):
        # Each entry is either a JSON response string (success) or an
        # Exception instance to raise - lets one fake client simulate a
        # Gemini API failure on a specific call in the sequence.
        self._responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return FakeResponse(item)


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


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


def make_connection_error() -> genai_errors.ServerError:
    return genai_errors.ServerError(code=503, response_json={"error": {"message": "overloaded"}})


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
    assert set(schema["required"]) == {"genre", "mood", "energy", "likes_acoustic", "seed_artist"}


def test_build_extraction_schema_constrains_seed_artist_to_catalog_plus_unspecified():
    schema = build_extraction_schema(["pop"], ["happy"], ["Neon Echo", "LoRoom"])

    assert schema["properties"]["seed_artist"]["enum"] == ["LoRoom", "Neon Echo", "unspecified"]


def test_build_extraction_schema_seed_artist_defaults_to_unspecified_only_when_no_catalog_artists_given():
    schema = build_extraction_schema(["pop"], ["happy"])

    assert schema["properties"]["seed_artist"]["enum"] == ["unspecified"]


def test_get_catalog_artists_returns_sorted_distinct_values():
    assert get_catalog_artists(make_small_catalog()) == ["LoRoom", "Neon Echo", "Paper Lanterns"]


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
    profile = {
        "genre": "unspecified", "mood": "unspecified", "energy": 0.5, "likes_acoustic": None,
        "seed_artist": "unspecified",
    }

    clamped = clamp_profile(profile)

    assert clamped["genre"] == ""
    assert clamped["mood"] == ""
    assert clamped["seed_artist"] == ""


def test_clamp_profile_leaves_real_seed_artist_unchanged():
    profile = {
        "genre": "pop", "mood": "happy", "energy": 0.5, "likes_acoustic": None,
        "seed_artist": "Neon Echo",
    }

    clamped = clamp_profile(profile)

    assert clamped["seed_artist"] == "Neon Echo"


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
    explanation_call = client.models.calls[1]
    song_id_enum = explanation_call["config"].response_json_schema["properties"][
        "song_notes"
    ]["items"]["properties"]["song_id"]["enum"]
    assert set(song_id_enum) == recommended_ids


def test_has_api_key_true_when_env_var_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")

    assert has_api_key() is True


def test_has_api_key_false_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

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
    assert len(client.models.calls) == 1


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

    explanation_call = client.models.calls[1]
    user_content = explanation_call["contents"]
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


def test_run_nl_query_seed_artist_boost_reaches_scoring_and_grounding_notes(monkeypatch):
    from src import similarity_store

    # Deterministic stand-in for the real on-disk similarity graph: pretend
    # "Neon Echo" (the seed) is similar to "LoRoom", a real artist actually
    # present in SIX_SONG_CATALOG, so the wiring can be checked independent
    # of whatever the real data/similarity.db happens to contain.
    monkeypatch.setattr(
        similarity_store, "similarity_boost_map",
        lambda seed_artist, limit=5: {"LoRoom": 0.9} if seed_artist == "Neon Echo" else {},
    )

    profile_response = json.dumps(
        {
            "genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True,
            "seed_artist": "Neon Echo",
        }
    )
    explanation_response = json.dumps(
        {"summary": "Great chill picks, plus some similar to Neon Echo.", "song_notes": [{"song_id": 1, "note": "matches"}]}
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(SIX_SONG_CATALOG, "chill lofi songs like Neon Echo", client)

    assert result["status"] == "ok"
    # LoRoom's songs (ids 1 and 3) should now outscore Paper Lanterns' (id 2)
    # equally-lofi/chill song, purely due to the similarity boost.
    loroom_score = next(score for song, score, _ in result["recommendations"] if song["id"] == 1)
    paper_lanterns_score = next(score for song, score, _ in result["recommendations"] if song["id"] == 2)
    assert loroom_score > paper_lanterns_score

    explanation_call = client.models.calls[1]
    assert "Neon Echo" in explanation_call["contents"]
    assert "LoRoom" in explanation_call["contents"]
    assert "musically similar" in explanation_call["contents"]


def test_run_nl_query_without_seed_artist_applies_no_similarity_boost(monkeypatch):
    from src import similarity_store

    monkeypatch.setattr(
        similarity_store, "similarity_boost_map",
        lambda seed_artist, limit=5: (_ for _ in ()).throw(
            AssertionError("similarity_boost_map should not find a match for an empty seed_artist")
        ) if seed_artist else {},
    )

    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True, "seed_artist": "unspecified"}
    )
    explanation_response = json.dumps(
        {"summary": "Great chill picks.", "song_notes": [{"song_id": 1, "note": "matches"}]}
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(SIX_SONG_CATALOG, "chill lofi songs", client)

    assert result["status"] == "ok"
    explanation_call = client.models.calls[1]
    assert "musically similar" not in explanation_call["contents"]


def test_run_nl_query_seed_artist_mention_does_not_trip_the_grounding_guardrail(monkeypatch):
    from src import similarity_store

    monkeypatch.setattr(similarity_store, "similarity_boost_map", lambda seed_artist, limit=5: {})

    profile_response = json.dumps(
        {
            "genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True,
            "seed_artist": "Grave Circuit",
        }
    )
    # "Grave Circuit" is a real catalog artist (Iron Verdict, id 6) that
    # scores too low to be recommended for this profile - without the
    # extra_allowed_artists carve-out, naming it here would incorrectly trip
    # check_grounding exactly like the test above, even though the user
    # themselves named it as a reference artist.
    explanation_response = json.dumps(
        {
            "summary": "Since you mentioned Grave Circuit, here's something gentler that still fits your mood.",
            "song_notes": [{"song_id": 1, "note": "matches your mood"}],
        }
    )
    client = FakeClient([profile_response, explanation_response])

    result = run_nl_query(SIX_SONG_CATALOG, "chill lofi songs like Grave Circuit", client)

    assert result["status"] == "ok"
    assert result["explanation"]["summary"].startswith("Since you mentioned Grave Circuit")


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


def test_run_session_demo_reports_correct_suppressed_count(capsys):
    profile_response = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    ok_explanation = json.dumps(
        {"summary": "Great picks.", "song_notes": [{"song_id": 1, "note": "matches"}]}
    )
    # Second query's explanation mentions "Iron Verdict" - a real SIX_SONG_CATALOG
    # song that scores far too low to be recommended for this profile, so it
    # trips check_grounding (same scope-creep scenario as the guardrail test above).
    tripped_explanation = json.dumps(
        {
            "summary": "If you want something different, Iron Verdict brings a lot of energy!",
            "song_notes": [{"song_id": 1, "note": "matches your mood"}],
        }
    )
    client = FakeClient([profile_response, ok_explanation, profile_response, tripped_explanation])

    run_session_demo(SIX_SONG_CATALOG, client, queries=["chill lofi songs", "chill lofi songs again"])

    captured = capsys.readouterr()
    assert "1 of 2 explanations were suppressed by the grounding guardrail." in captured.out


def test_run_nl_query_raises_value_error_for_empty_query_before_any_gemini_call():
    client = FakeClient([])

    try:
        run_nl_query(SMALL_CATALOG, "", client)
        assert False, "expected ValueError for empty query"
    except ValueError:
        pass

    assert client.models.calls == []


def test_clamp_profile_handles_missing_genre_and_mood_keys():
    profile = {"energy": 0.5, "likes_acoustic": None}

    clamped = clamp_profile(profile)

    assert clamped["energy"] == 0.5


def test_clamp_profile_leaves_likes_acoustic_unchanged():
    for value in (True, False, None):
        profile = {"genre": "pop", "mood": "happy", "energy": 0.5, "likes_acoustic": value}

        clamped = clamp_profile(profile)

        assert clamped["likes_acoustic"] is value


def test_format_fallback_table_includes_every_recommendation():
    recommendations = [
        ({"id": 1, "title": "Sunrise City", "artist": "Neon Echo"}, 4.25, "genre matches"),
        ({"id": 2, "title": "Midnight Coding", "artist": "LoRoom"}, 3.10, "mood matches"),
    ]

    table = format_fallback_table({"genre": "pop", "mood": "happy"}, recommendations)

    assert "Sunrise City" in table
    assert "Midnight Coding" in table


def test_format_fallback_table_uses_any_placeholder_for_unspecified_genre_and_mood():
    recommendations = [({"id": 1, "title": "Sunrise City", "artist": "Neon Echo"}, 4.25, "energy matches")]

    table = format_fallback_table({"genre": "", "mood": ""}, recommendations)

    assert "(any)" in table


def test_build_extraction_schema_with_empty_catalog_vocabulary():
    schema = build_extraction_schema([], [])

    assert schema["properties"]["genre"]["enum"] == ["unspecified"]
    assert schema["properties"]["mood"]["enum"] == ["unspecified"]
