"""
Textual guardrail net (Stage 4 of the RAG plan).

The primary anti-hallucination guardrail is structural: build_explanation_schema()
in src/nl_interface.py enum-constrains every song_id in song_notes to the
exact recommended set, so Gemini cannot structurally return an out-of-scope
song reference there. check_grounding() below is a secondary net for the one
place that constraint doesn't reach: the free-text "summary" (and each
song_note's free-text "note"), where Gemini could still namedrop a song in
prose.

Scope, by design: this is exact, case-insensitive whole-phrase matching
against the catalog's own titles/artists - nothing fuzzier. It can catch
Gemini mentioning a REAL catalog song/artist that wasn't recommended (scope
creep). It CANNOT catch a wholly invented title/artist that matches nothing
in the catalog - there is nothing to compare an invented string against
without fuzzy/NER-style detection, which would reintroduce the false-
positive/false-negative ambiguity this stage deliberately avoids. That
residual case is still covered - by the structural schema constraint, not
this check.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GroundingResult:
    passed: bool
    violation: Optional[str] = None


def _contains_whole_phrase(text: str, phrase: str) -> bool:
    """Case-insensitive whole-word/phrase match, so a short title/artist
    name can't false-positive on a partial match inside a longer word
    (e.g. a title "Home" must not match inside "homegrown").
    """
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def check_grounding(
    explanation_text: str,
    allowed_songs: List[Dict],
    catalog_songs: List[Dict],
    extra_allowed_artists: Optional[List[str]] = None,
) -> GroundingResult:
    """Flags the first mention of a catalog title/artist that isn't part of
    `allowed_songs` (the actual recommendation set), found by scanning
    `catalog_songs` (the full catalog) for anything not in that allowed set.

    extra_allowed_artists covers a legitimate case this wasn't otherwise built
    for: a natural-language query naming a reference/seed artist (e.g. "songs
    like Neon Echo") that the explanation may reasonably repeat even when that
    artist isn't itself among the recommended songs. Without this carve-out,
    such a mention would be indistinguishable from real scope creep and would
    false-positive-trip this guardrail. Titles are unaffected - only the seed
    artist's own tracks stay off-limits unless actually recommended.
    """
    allowed_titles = {song["title"] for song in allowed_songs}
    allowed_artists = {song["artist"] for song in allowed_songs} | set(extra_allowed_artists or [])

    for song in catalog_songs:
        if song["title"] not in allowed_titles and _contains_whole_phrase(
            explanation_text, song["title"]
        ):
            return GroundingResult(passed=False, violation=song["title"])
        if song["artist"] not in allowed_artists and _contains_whole_phrase(
            explanation_text, song["artist"]
        ):
            return GroundingResult(passed=False, violation=song["artist"])

    return GroundingResult(passed=True, violation=None)
