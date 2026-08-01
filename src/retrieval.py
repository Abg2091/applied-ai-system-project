"""
Grounding corpus for the explanation layer (Stage 3 of the RAG plan).

Deliberately a plain keyed lookup, not a similarity index: with one short
note per genre/artist actually present in the catalog (data/knowledge/), a
from-scratch TF-IDF or embedding-based retriever would add tokenization
edge cases and numerical machinery this project doesn't need.

lookup_notes() is pure dictionary lookup - no ranking, no scoring, no
numerical edge cases - and is fully testable without touching disk.
get_notes() is the thin wrapper that loads the on-disk corpus for it.

A genre/artist with no matching note is simply omitted, never invented -
see EXPLANATION_SYSTEM_PROMPT in nl_interface.py, which instructs Claude to
say nothing about anything grounding_notes doesn't cover, rather than guess.
"""

import json
from pathlib import Path
from typing import Dict, List

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def _load_json(filename: str) -> Dict[str, str]:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_genre_notes() -> Dict[str, str]:
    return _load_json("genre_notes.json")


def load_artist_notes() -> Dict[str, str]:
    return _load_json("artist_notes.json")


def lookup_notes(
    genres: List[str],
    artists: List[str],
    genre_notes: Dict[str, str],
    artist_notes: Dict[str, str],
) -> List[str]:
    """Returns one note per genre/artist that has one, in order, with
    duplicate notes removed (recommended songs often share a genre/artist).
    A missing key is silently skipped rather than raising or fabricating.
    """
    notes: List[str] = []
    seen = set()

    for genre in genres:
        note = genre_notes.get(genre)
        if note and note not in seen:
            notes.append(note)
            seen.add(note)

    for artist in artists:
        note = artist_notes.get(artist)
        if note and note not in seen:
            notes.append(note)
            seen.add(note)

    return notes


def get_notes(genres: List[str], artists: List[str]) -> List[str]:
    """Convenience wrapper: loads the on-disk corpus and looks up notes for
    the given genres/artists - typically the genres/artists appearing in
    the current recommendation set, not the whole catalog.
    """
    return lookup_notes(genres, artists, load_genre_notes(), load_artist_notes())
