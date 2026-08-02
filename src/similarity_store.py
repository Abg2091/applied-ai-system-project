"""
Second retrieval source for the explanation/scoring layer: an artist-
similarity graph backed by SQLite (data/similarity.db), built offline by
scripts/build_similarity_db.py from the catalog's own numeric features
(energy/tempo_bpm/valence/danceability/acousticness) - not a fuzzy text/
embedding index, so this doesn't reopen the over-engineered-retrieval
guardrail src/retrieval.py's docstring closes.

Same missing-key philosophy as src/retrieval.py: an artist with no rows (or
a missing/empty database) simply yields no boost - never fabricated.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "similarity.db"


def get_similar_artists(artist: str, limit: int = 5) -> List[Tuple[str, float]]:
    """Returns up to `limit` (other_artist, weight) pairs similar to `artist`,
    ordered by weight descending. Returns [] if the database file doesn't
    exist or the artist has no rows - mirrors retrieval.py's missing-key
    behavior rather than raising.
    """
    if not artist or not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            "SELECT artist_b, weight FROM artist_similarity WHERE artist_a = ? "
            "ORDER BY weight DESC LIMIT ?",
            (artist, limit),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def similarity_boost_map(seed_artist: str, limit: int = 5) -> Dict[str, float]:
    """Convenience wrapper for recommend_songs()'s similarity_boost
    parameter: {artist_name: weight}, empty when there's no seed artist or
    it has no matches.
    """
    if not seed_artist:
        return {}
    return dict(get_similar_artists(seed_artist, limit))
