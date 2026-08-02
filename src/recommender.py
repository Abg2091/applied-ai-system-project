import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

GENRE_WEIGHT = 0.5
MOOD_WEIGHT = 2.0
ENERGY_WEIGHT = 3.0
ACOUSTIC_WEIGHT = 1.0
SIMILARITY_WEIGHT = 1.5

MAX_SONGS_PER_ARTIST = 2


def _normalize(value: str) -> str:
    """Case/whitespace-insensitive comparison so 'R&B' vs 'r&b' still matches."""
    return value.strip().lower()


def _score_breakdown(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    fav_genre: str,
    fav_mood: str,
    target_energy: float,
    likes_acoustic: Optional[bool] = None,
    artist: Optional[str] = None,
    similarity_boost: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Each weighted scoring component for one song, keyed by name; the total score is their sum."""
    breakdown = {
        "genre": GENRE_WEIGHT if _normalize(genre) == _normalize(fav_genre) else 0.0,
        "mood": MOOD_WEIGHT if _normalize(mood) == _normalize(fav_mood) else 0.0,
        "energy": ENERGY_WEIGHT * (1 - abs(energy - target_energy)),
    }
    if likes_acoustic is not None:
        acoustic_fit = acousticness if likes_acoustic else (1 - acousticness)
        breakdown["acoustic"] = ACOUSTIC_WEIGHT * acoustic_fit
    if similarity_boost:
        breakdown["similarity"] = SIMILARITY_WEIGHT * similarity_boost.get(artist, 0.0)
    return breakdown


def _score_song(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    fav_genre: str,
    fav_mood: str,
    target_energy: float,
    likes_acoustic: Optional[bool] = None,
    artist: Optional[str] = None,
    similarity_boost: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    """Scores one song against a user's preferences; shared by both the dict-based and dataclass-based paths."""
    breakdown = _score_breakdown(
        genre, mood, energy, acousticness, fav_genre, fav_mood, target_energy,
        likes_acoustic, artist, similarity_boost,
    )
    reasons = []

    if breakdown["genre"] > 0:
        reasons.append(f"genre '{genre}' matches your favorite")

    if breakdown["mood"] > 0:
        reasons.append(f"mood '{mood}' fits what you're looking for")

    energy_closeness = 1 - abs(energy - target_energy)
    if energy_closeness > 0.85:
        reasons.append(f"energy ({energy:.2f}) is close to your target ({target_energy:.2f})")

    if likes_acoustic is not None:
        acoustic_fit = acousticness if likes_acoustic else (1 - acousticness)
        if acoustic_fit > 0.7:
            reasons.append("acoustic level fits your preference")

    if breakdown.get("similarity", 0.0) > SIMILARITY_WEIGHT * 0.5:
        reasons.append(f"artist '{artist}' is musically similar to your reference artist")

    if not reasons:
        reasons.append("closest overall match available")

    return sum(breakdown.values()), reasons


def _select_diverse_top_k(scored: List, k: int, get_artist) -> List:
    """Picks the top k from an already-sorted list, capping how many can share the same artist."""
    if k <= 0:
        return []

    selected = []
    artist_counts = {}
    for item in scored:
        artist = get_artist(item)
        if artist_counts.get(artist, 0) >= MAX_SONGS_PER_ARTIST:
            continue
        selected.append(item)
        artist_counts[artist] = artist_counts.get(artist, 0) + 1
        if len(selected) == k:
            break
    return selected

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        scored = [
            (
                _score_song(
                    song.genre,
                    song.mood,
                    song.energy,
                    song.acousticness,
                    user.favorite_genre,
                    user.favorite_mood,
                    user.target_energy,
                    user.likes_acoustic,
                )[0],
                song,
            )
            for song in self.songs
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected = _select_diverse_top_k(scored, k, get_artist=lambda pair: pair[1].artist)
        return [song for _, song in selected]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = _score_song(
            song.genre,
            song.mood,
            song.energy,
            song.acousticness,
            user.favorite_genre,
            user.favorite_mood,
            user.target_energy,
            user.likes_acoustic,
        )
        return "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    numeric_fields = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")
    with open(csv_path, newline="", encoding="utf-8") as f:
        songs = []
        for row in csv.DictReader(f):
            row["id"] = int(row["id"])
            for field in numeric_fields:
                row[field] = float(row[field])
            songs.append(row)
        print(f"Loaded {len(songs)} songs from {csv_path}.")
        return songs

def score_song(
    user_prefs: Dict, song: Dict, similarity_boost: Optional[Dict[str, float]] = None
) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    similarity_boost is an optional {artist: weight} map (see
    src/similarity_store.py) from a reference artist a natural-language query
    named - None/empty leaves scoring exactly as before.
    """
    return _score_song(
        song["genre"],
        song["mood"],
        song["energy"],
        song["acousticness"],
        user_prefs["genre"],
        user_prefs["mood"],
        user_prefs["energy"],
        user_prefs.get("likes_acoustic"),
        song["artist"],
        similarity_boost,
    )

def score_breakdown(
    user_prefs: Dict, song: Dict, similarity_boost: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Returns each weighted scoring component (genre, mood, energy, and optionally
    acoustic/similarity) for one song, so callers can display how its total
    score was built.
    Required by src/main.py's breakdown display.
    """
    return _score_breakdown(
        song["genre"],
        song["mood"],
        song["energy"],
        song["acousticness"],
        user_prefs["genre"],
        user_prefs["mood"],
        user_prefs["energy"],
        user_prefs.get("likes_acoustic"),
        song["artist"],
        similarity_boost,
    )

def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    similarity_boost: Optional[Dict[str, float]] = None,
) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    similarity_boost: optional {artist: weight} map nudging scores toward
    artists similar to a reference artist a query named (src/similarity_store.py).
    None (the default) reproduces today's scores/order exactly.
    """
    scored = [(song, *score_song(user_prefs, song, similarity_boost)) for song in songs]
    scored.sort(key=lambda triple: triple[1], reverse=True)
    selected = _select_diverse_top_k(scored, k, get_artist=lambda triple: triple[0]["artist"])
    return [(song, score, "; ".join(reasons)) for song, score, reasons in selected]
