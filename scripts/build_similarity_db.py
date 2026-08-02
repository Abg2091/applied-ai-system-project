"""
Builds data/similarity.db, the artist-similarity graph used by
src/similarity_store.py (Stage A of the multi-source retrieval extension).

Deliberately numeric-feature similarity, not text/embedding similarity: each
artist's catalog rows are averaged into one vector over
energy/tempo_bpm/valence/danceability/acousticness (already in
data/songs.csv), min-max normalized so tempo_bpm's much larger scale doesn't
dominate the distance, and the top-K nearest other artists are stored per
artist. This is a precomputed, static artifact - same philosophy as
data/knowledge/*.json - so nothing at query time needs pandas or numpy.

Run once and commit the resulting data/similarity.db:
    python scripts/build_similarity_db.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = REPO_ROOT / "data" / "songs.csv"
DB_PATH = REPO_ROOT / "data" / "similarity.db"

FEATURES = ["energy", "tempo_bpm", "valence", "danceability", "acousticness"]
TOP_K = 5


def build_artist_vectors(songs_csv: Path) -> pd.DataFrame:
    """One row per artist: the mean of each feature across that artist's
    songs, min-max normalized per feature so no single feature's raw scale
    (e.g. tempo_bpm's 60-170 vs acousticness's 0-1) dominates distance.
    """
    songs = pd.read_csv(songs_csv)
    artist_vectors = songs.groupby("artist")[FEATURES].mean()

    normalized = artist_vectors.copy()
    for feature in FEATURES:
        low, high = artist_vectors[feature].min(), artist_vectors[feature].max()
        spread = high - low
        normalized[feature] = (artist_vectors[feature] - low) / spread if spread > 0 else 0.5

    return normalized


def compute_top_k_similarities(artist_vectors: pd.DataFrame, top_k: int = TOP_K) -> list:
    """Returns (artist_a, artist_b, weight) rows: for each artist, its top_k
    nearest other artists by normalized-feature Euclidean distance, weight =
    1 / (1 + distance) so closer artists score nearer 1.0.
    """
    artists = list(artist_vectors.index)
    rows = []

    for artist_a in artists:
        vector_a = artist_vectors.loc[artist_a]
        distances = []
        for artist_b in artists:
            if artist_b == artist_a:
                continue
            distance = ((vector_a - artist_vectors.loc[artist_b]) ** 2).sum() ** 0.5
            distances.append((artist_b, 1.0 / (1.0 + distance)))

        distances.sort(key=lambda pair: pair[1], reverse=True)
        for artist_b, weight in distances[:top_k]:
            rows.append((artist_a, artist_b, weight))

    return rows


def write_similarity_db(rows: list, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS artist_similarity")
        conn.execute(
            """
            CREATE TABLE artist_similarity (
                artist_a TEXT NOT NULL,
                artist_b TEXT NOT NULL,
                weight REAL NOT NULL,
                PRIMARY KEY (artist_a, artist_b)
            )
            """
        )
        conn.executemany(
            "INSERT INTO artist_similarity (artist_a, artist_b, weight) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    artist_vectors = build_artist_vectors(SONGS_CSV)
    rows = compute_top_k_similarities(artist_vectors)
    write_similarity_db(rows, DB_PATH)
    print(f"Wrote {len(rows)} artist_similarity rows for {len(artist_vectors)} artists to {DB_PATH}.")


if __name__ == "__main__":
    main()
