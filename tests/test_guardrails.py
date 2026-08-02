from src.guardrails import check_grounding

CATALOG = [
    {"id": 1, "title": "Sunrise City", "artist": "Neon Echo"},
    {"id": 2, "title": "Midnight Coding", "artist": "LoRoom"},
    {"id": 3, "title": "Storm Runner", "artist": "Voltline"},
]

ALLOWED = [CATALOG[0], CATALOG[1]]  # Sunrise City / Neon Echo + Midnight Coding / LoRoom recommended


def test_check_grounding_passes_when_text_only_mentions_allowed_songs():
    text = "Sunrise City by Neon Echo and Midnight Coding by LoRoom both fit your mood."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is True
    assert result.violation is None


def test_check_grounding_flags_mention_of_non_recommended_catalog_title():
    text = "You might also like Storm Runner for something more intense."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is False
    assert result.violation == "Storm Runner"


def test_check_grounding_flags_mention_of_non_recommended_catalog_artist():
    text = "Voltline has a similar vibe if you want more energy."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is False
    assert result.violation == "Voltline"


def test_check_grounding_matching_is_case_insensitive():
    text = "check out storm runner sometime"

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is False
    assert result.violation == "Storm Runner"


def test_check_grounding_does_not_flag_partial_word_matches():
    # Neither catalog entry's title/artist should match inside an unrelated word.
    text = "This is a great homegrown playlist for your morning routine."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is True


def test_check_grounding_allows_artist_mentioned_via_a_different_allowed_song():
    text = "Neon Echo really nails that upbeat pop energy."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is True


def test_check_grounding_with_empty_text_passes():
    result = check_grounding("", ALLOWED, CATALOG)

    assert result.passed is True


def test_check_grounding_returns_first_violation_in_catalog_order_when_multiple_present():
    catalog = CATALOG + [{"id": 4, "title": "Night Fall", "artist": "Echo Drift"}]
    text = "Both Night Fall and Storm Runner would fit that vibe."

    result = check_grounding(text, ALLOWED, catalog)

    # Storm Runner (catalog index 2) is checked before Night Fall (index 3),
    # regardless of which one is mentioned first in the text.
    assert result.passed is False
    assert result.violation == "Storm Runner"


def test_check_grounding_flags_mention_with_adjacent_punctuation():
    text = "You'd love Storm Runner! It's got great energy."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is False
    assert result.violation == "Storm Runner"


def test_check_grounding_does_not_cross_match_when_one_catalog_title_is_a_substring_of_another():
    catalog = [
        {"id": 1, "title": "Home", "artist": "Solo Artist"},
        {"id": 2, "title": "Homegrown Nights", "artist": "Field Records"},
    ]
    allowed = [catalog[1]]  # only "Homegrown Nights" was recommended; "Home" was not
    text = "Homegrown Nights really captures that late-summer feeling."

    result = check_grounding(text, allowed, catalog)

    assert result.passed is True


def test_check_grounding_still_flags_non_recommended_artist_when_extra_allowed_artists_is_none():
    text = "Voltline has a similar vibe if you want more energy."

    result = check_grounding(text, ALLOWED, CATALOG, extra_allowed_artists=None)

    assert result.passed is False
    assert result.violation == "Voltline"


def test_check_grounding_allows_a_legitimate_seed_artist_mention_via_extra_allowed_artists():
    # Voltline is a real catalog artist not in ALLOWED - representing a
    # user-named reference/seed artist ("songs like Voltline") that the
    # explanation may legitimately repeat even though Voltline itself wasn't
    # recommended this time.
    text = "Since you mentioned Voltline, these picks share a similar energy."

    result = check_grounding(text, ALLOWED, CATALOG, extra_allowed_artists=["Voltline"])

    assert result.passed is True


def test_check_grounding_extra_allowed_artists_does_not_whitelist_that_artists_titles():
    # The carve-out is artist-name-only: Storm Runner (Voltline's track)
    # still isn't recommended, so naming the title itself must still trip.
    text = "Since you mentioned Voltline, you'd also love Storm Runner."

    result = check_grounding(text, ALLOWED, CATALOG, extra_allowed_artists=["Voltline"])

    assert result.passed is False
    assert result.violation == "Storm Runner"


def test_check_grounding_extra_allowed_artists_does_not_whitelist_other_non_recommended_artists():
    catalog = CATALOG + [{"id": 4, "title": "Night Fall", "artist": "Echo Drift"}]
    text = "Echo Drift also has a similar vibe."

    result = check_grounding(text, ALLOWED, catalog, extra_allowed_artists=["Voltline"])

    assert result.passed is False
    assert result.violation == "Echo Drift"


def test_check_grounding_cannot_catch_a_wholly_fabricated_name_not_in_the_catalog():
    # Documented scope limitation: exact-match-only detection can catch a
    # mention of a REAL catalog song/artist outside the allowed set, but a
    # completely invented name matches nothing to compare against, so it
    # passes here. The actual protection against a fabricated song is the
    # explanation schema's song_id enum constraint (see
    # build_explanation_schema in src/nl_interface.py) - this textual check
    # is a secondary net, not the primary guardrail.
    text = "You'd also enjoy 'Fake Song' by 'Nonexistent Artist'."

    result = check_grounding(text, ALLOWED, CATALOG)

    assert result.passed is True
