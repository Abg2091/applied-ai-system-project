from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    _score_song,
    SIMILARITY_WEIGHT,
    recommend_songs,
    score_breakdown,
    score_song,
)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_conflicting_mood_and_energy_scores_without_crashing():
    # One song matches mood but not energy; the other matches energy but not mood.
    songs = [
        Song(
            id=1,
            title="Mood Match, Wrong Energy",
            artist="Artist A",
            genre="classical",
            mood="melancholic",
            energy=0.2,
            tempo_bpm=60,
            valence=0.2,
            danceability=0.2,
            acousticness=0.9,
        ),
        Song(
            id=2,
            title="Energy Match, Wrong Mood",
            artist="Artist B",
            genre="classical",
            mood="triumphant",
            energy=0.9,
            tempo_bpm=140,
            valence=0.8,
            danceability=0.7,
            acousticness=0.1,
        ),
    ]
    user = UserProfile(
        favorite_genre="classical",
        favorite_mood="melancholic",
        target_energy=0.9,
        likes_acoustic=True,
    )
    rec = Recommender(songs)

    results = rec.recommend(user, k=2)

    assert len(results) == 2
    for song in results:
        explanation = rec.explain_recommendation(user, song)
        assert explanation.strip() != ""


def test_unmatched_genre_and_mood_falls_back_to_closest_match():
    rec = make_small_recommender()
    # target_energy=0.55 keeps energy_closeness at or below 0.85 for both fixture
    # songs (0.75 and 0.85), and likes_acoustic=None disables the acoustic bonus,
    # so no partial-match reason can fire for either song.
    user = UserProfile(
        favorite_genre="opera",
        favorite_mood="furious",
        target_energy=0.55,
        likes_acoustic=None,
    )

    results = rec.recommend(user, k=2)

    assert len(results) == 2
    for song in results:
        explanation = rec.explain_recommendation(user, song)
        assert "closest overall match available" in explanation


def test_out_of_range_target_energy_does_not_raise():
    rec = make_small_recommender()
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=1.5,
        likes_acoustic=False,
    )

    results = rec.recommend(user, k=2)

    assert len(results) == 2


def test_genre_and_mood_matching_is_case_and_whitespace_insensitive():
    rec = make_small_recommender()
    song = rec.songs[0]  # genre="pop", mood="happy"

    messy_user = UserProfile(
        favorite_genre="  PoP ",
        favorite_mood="HAPPY",
        target_energy=0.8,
        likes_acoustic=False,
    )
    clean_user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    messy_score, _ = _score_song(
        song.genre, song.mood, song.energy, song.acousticness,
        messy_user.favorite_genre, messy_user.favorite_mood,
        messy_user.target_energy, messy_user.likes_acoustic,
    )
    clean_score, _ = _score_song(
        song.genre, song.mood, song.energy, song.acousticness,
        clean_user.favorite_genre, clean_user.favorite_mood,
        clean_user.target_energy, clean_user.likes_acoustic,
    )

    assert messy_score == clean_score


def test_diversity_cap_limits_songs_per_artist():
    songs = [
        Song(id=1, title="Same Artist 1", artist="Repeat Offender", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.8, acousticness=0.1),
        Song(id=2, title="Same Artist 2", artist="Repeat Offender", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.8, acousticness=0.1),
        Song(id=3, title="Same Artist 3", artist="Repeat Offender", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.8, acousticness=0.1),
        Song(id=4, title="Different Artist", artist="Someone Else", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.8, acousticness=0.1),
    ]
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = Recommender(songs)

    results = rec.recommend(user, k=3)

    repeat_offender_count = sum(1 for song in results if song.artist == "Repeat Offender")
    assert repeat_offender_count <= 2
    assert any(song.artist == "Someone Else" for song in results)


def test_recommend_with_k_zero_returns_empty_list():
    rec = make_small_recommender()
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    results = rec.recommend(user, k=0)

    assert results == []


DICT_USER_PREFS = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
DICT_SONG = {
    "id": 1, "title": "Test Pop Track", "artist": "Test Artist", "genre": "pop", "mood": "happy",
    "energy": 0.8, "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.2,
}


def test_score_song_with_no_similarity_boost_is_unchanged():
    with_none, _ = score_song(DICT_USER_PREFS, DICT_SONG, similarity_boost=None)
    without_param, _ = score_song(DICT_USER_PREFS, DICT_SONG)

    assert with_none == without_param


def test_score_song_applies_similarity_boost_for_matching_artist():
    boosted_score, reasons = score_song(
        DICT_USER_PREFS, DICT_SONG, similarity_boost={"Test Artist": 0.8}
    )
    unboosted_score, _ = score_song(DICT_USER_PREFS, DICT_SONG, similarity_boost=None)

    assert boosted_score == unboosted_score + SIMILARITY_WEIGHT * 0.8
    assert any("similar" in reason for reason in reasons)


def test_score_song_similarity_boost_ignores_unmatched_artist():
    score, _ = score_song(
        DICT_USER_PREFS, DICT_SONG, similarity_boost={"Some Other Artist": 0.9}
    )
    baseline, _ = score_song(DICT_USER_PREFS, DICT_SONG, similarity_boost=None)

    assert score == baseline


def test_score_breakdown_includes_similarity_component_only_when_boost_given():
    boosted = score_breakdown(DICT_USER_PREFS, DICT_SONG, similarity_boost={"Test Artist": 0.8})
    unboosted = score_breakdown(DICT_USER_PREFS, DICT_SONG, similarity_boost=None)

    assert boosted["similarity"] == SIMILARITY_WEIGHT * 0.8
    assert "similarity" not in unboosted


def test_recommend_songs_with_similarity_boost_reorders_candidates():
    songs = [
        {"id": 1, "title": "Neutral Match", "artist": "Neutral Artist", "genre": "rock", "mood": "intense",
         "energy": 0.5, "tempo_bpm": 100, "valence": 0.5, "danceability": 0.5, "acousticness": 0.5},
        {"id": 2, "title": "Similar Artist Track", "artist": "Similar Artist", "genre": "rock", "mood": "intense",
         "energy": 0.5, "tempo_bpm": 100, "valence": 0.5, "danceability": 0.5, "acousticness": 0.5},
    ]
    user_prefs = {"genre": "rock", "mood": "intense", "energy": 0.5, "likes_acoustic": None}

    unboosted = recommend_songs(user_prefs, songs, k=2)
    assert unboosted[0][0]["id"] == unboosted[1][0]["id"] or unboosted[0][1] == unboosted[1][1]

    boosted = recommend_songs(user_prefs, songs, k=2, similarity_boost={"Similar Artist": 1.0})
    assert boosted[0][0]["artist"] == "Similar Artist"


def test_recommend_songs_similarity_boost_none_matches_no_boost_argument():
    songs = [DICT_SONG]

    with_none = recommend_songs(DICT_USER_PREFS, songs, k=1, similarity_boost=None)
    without_param = recommend_songs(DICT_USER_PREFS, songs, k=1)

    assert with_none == without_param
