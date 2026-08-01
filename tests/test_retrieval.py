from src.retrieval import get_notes, load_artist_notes, load_genre_notes, lookup_notes

GENRE_NOTES = {"pop": "Pop note.", "lofi": "Lofi note."}
ARTIST_NOTES = {"Neon Echo": "Neon Echo note.", "LoRoom": "LoRoom note."}


def test_lookup_notes_returns_note_for_present_genre_and_artist():
    notes = lookup_notes(["pop"], ["Neon Echo"], GENRE_NOTES, ARTIST_NOTES)

    assert notes == ["Pop note.", "Neon Echo note."]


def test_lookup_notes_omits_missing_keys_silently():
    notes = lookup_notes(["opera"], ["Nonexistent Artist"], GENRE_NOTES, ARTIST_NOTES)

    assert notes == []


def test_lookup_notes_mixes_present_and_missing_keys():
    notes = lookup_notes(["pop", "opera"], ["Nonexistent Artist", "LoRoom"], GENRE_NOTES, ARTIST_NOTES)

    assert notes == ["Pop note.", "LoRoom note."]


def test_lookup_notes_dedupes_repeated_notes():
    # Two recommended songs sharing a genre should not produce a duplicate note.
    notes = lookup_notes(["pop", "pop"], ["Neon Echo", "Neon Echo"], GENRE_NOTES, ARTIST_NOTES)

    assert notes == ["Pop note.", "Neon Echo note."]


def test_lookup_notes_with_empty_input_returns_empty_list():
    assert lookup_notes([], [], GENRE_NOTES, ARTIST_NOTES) == []


def test_lookup_notes_with_empty_corpus_returns_empty_list():
    assert lookup_notes(["pop"], ["Neon Echo"], {}, {}) == []


def test_load_genre_notes_reads_the_real_corpus_file():
    genre_notes = load_genre_notes()

    assert "lofi" in genre_notes
    assert genre_notes["lofi"].strip() != ""


def test_load_artist_notes_reads_the_real_corpus_file():
    artist_notes = load_artist_notes()

    assert "LoRoom" in artist_notes
    assert artist_notes["LoRoom"].strip() != ""


def test_get_notes_looks_up_against_the_real_on_disk_corpus():
    notes = get_notes(genres=["lofi"], artists=["LoRoom"])

    assert len(notes) == 2
    assert all(isinstance(note, str) and note.strip() for note in notes)


def test_get_notes_returns_empty_list_for_genre_and_artist_not_in_the_catalog():
    notes = get_notes(genres=["opera"], artists=["Totally Fictional Artist"])

    assert notes == []
