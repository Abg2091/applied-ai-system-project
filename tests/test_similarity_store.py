import sqlite3

from src import similarity_store
from src.similarity_store import get_similar_artists, similarity_boost_map


def _make_db(tmp_path):
    db_path = tmp_path / "similarity.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE artist_similarity (artist_a TEXT, artist_b TEXT, weight REAL)"
    )
    conn.executemany(
        "INSERT INTO artist_similarity VALUES (?, ?, ?)",
        [
            ("Neon Echo", "LoRoom", 0.9),
            ("Neon Echo", "Voltline", 0.5),
            ("Neon Echo", "Max Pulse", 0.7),
            ("LoRoom", "Neon Echo", 0.9),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_get_similar_artists_orders_by_weight_descending(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    result = get_similar_artists("Neon Echo")

    assert result == [
        ("LoRoom", 0.9),
        ("Max Pulse", 0.7),
        ("Voltline", 0.5),
    ]


def test_get_similar_artists_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    result = get_similar_artists("Neon Echo", limit=1)

    assert result == [("LoRoom", 0.9)]


def test_get_similar_artists_returns_empty_list_for_unknown_artist(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    assert get_similar_artists("Totally Fictional Artist") == []


def test_get_similar_artists_returns_empty_list_for_empty_artist_name(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    assert get_similar_artists("") == []


def test_get_similar_artists_returns_empty_list_when_db_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", tmp_path / "does_not_exist.db")

    assert get_similar_artists("Neon Echo") == []


def test_similarity_boost_map_returns_dict_of_artist_to_weight(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    boost = similarity_boost_map("Neon Echo")

    assert boost == {"LoRoom": 0.9, "Max Pulse": 0.7, "Voltline": 0.5}


def test_similarity_boost_map_returns_empty_dict_for_no_seed_artist(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    assert similarity_boost_map("") == {}


def test_similarity_boost_map_returns_empty_dict_for_unmatched_seed_artist(tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_store, "DB_PATH", _make_db(tmp_path))

    assert similarity_boost_map("Totally Fictional Artist") == {}


def test_get_similar_artists_reads_the_real_on_disk_similarity_db():
    result = get_similar_artists("Neon Echo")

    assert len(result) > 0
    assert all(isinstance(artist, str) and isinstance(weight, float) for artist, weight in result)
