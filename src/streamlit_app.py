"""
Streamlit UI for the Music Recommender Simulation.

Two modes, both backed by the same underlying logic already used by the CLI
(src/main.py) and the natural-language layer (src/nl_interface.py) - this file
adds no new scoring, loading, or orchestration of its own:

- Guided Search: a structured form (genre/mood/energy/acoustic) wired to
  src.recommender.recommend_songs/score_breakdown.
- Ask in Plain English: a free-text box wired to src.nl_interface.run_nl_query,
  disabled with an inline message when GEMINI_API_KEY isn't set.

Run with: streamlit run src/streamlit_app.py
"""

import os
import sys

# Make `from src.xxx import ...` resolve regardless of the CWD `streamlit run`
# was invoked from - streamlit puts this file's own folder (src/) on
# sys.path[0], not the repo root, same as `python src/streamlit_app.py` would.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from src.confidence import score_confidence
from src.nl_interface import get_catalog_vocabulary, has_api_key, run_nl_query, validate_query_length
from src.recommender import load_songs, recommend_songs, score_breakdown

CSV_PATH = os.path.join(_REPO_ROOT, "data", "songs.csv")


@st.cache_data
def _load_songs_cached(csv_path: str):
    return load_songs(csv_path)


def render_confidence(confidence):
    st.caption(f"Confidence: **{confidence.tier}** ({confidence.score:.2f}) — {confidence.reason}")


def render_recommendation(rank, song, score, reasons, user_prefs):
    breakdown = score_breakdown(user_prefs, song)
    label = f"{rank}. {song['title']} — {song['artist']} (score {score:.2f})"
    with st.expander(label, expanded=(rank == 1)):
        cols = st.columns(len(breakdown))
        for col, (component, value) in zip(cols, breakdown.items()):
            col.metric(component.capitalize(), f"{value:+.2f}")
        st.markdown("**Why this matches:**")
        for reason in reasons.split("; "):
            st.markdown(f"- {reason}")


def render_guided_search(songs, catalog_genres, catalog_moods):
    with st.form("guided_search_form"):
        genre = st.selectbox("Genre", ["(no preference)"] + catalog_genres)
        mood = st.selectbox("Mood", ["(no preference)"] + catalog_moods)
        energy = st.slider("Energy (0 = calm, 1 = high-energy)", 0.0, 1.0, 0.5, step=0.05)
        acoustic_choice = st.radio(
            "Acoustic preference",
            ["No preference", "Yes, I like acoustic", "No, I prefer produced/electronic"],
            horizontal=True,
        )
        submitted = st.form_submit_button("Get Recommendations")

    if not submitted:
        return

    likes_acoustic = {
        "No preference": None,
        "Yes, I like acoustic": True,
        "No, I prefer produced/electronic": False,
    }[acoustic_choice]

    user_prefs = {
        "genre": "" if genre == "(no preference)" else genre,
        "mood": "" if mood == "(no preference)" else mood,
        "energy": energy,
        "likes_acoustic": likes_acoustic,
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)
    st.subheader(f"Top {len(recommendations)} Recommendations")
    render_confidence(score_confidence(user_prefs, recommendations))
    for rank, (song, score, reasons) in enumerate(recommendations, start=1):
        render_recommendation(rank, song, score, reasons, user_prefs)


def render_nl_query(songs):
    if not has_api_key():
        st.info(
            "Set GEMINI_API_KEY in your .env file to enable natural-language queries "
            "(copy .env.example to .env and fill it in)."
        )
        return

    if "gemini_client" not in st.session_state:
        from src.llm_client import get_client

        st.session_state["gemini_client"] = get_client()

    query = st.text_area(
        "What are you in the mood for?",
        placeholder="e.g. chill lofi songs for studying late at night",
        max_chars=500,
    )
    ask_clicked = st.button("Ask")

    if ask_clicked:
        try:
            validate_query_length(query)
        except ValueError as e:
            st.warning(str(e))
        else:
            with st.spinner("Thinking..."):
                result = run_nl_query(songs, query, st.session_state["gemini_client"])
            st.session_state["nl_result"] = result

    result = st.session_state.get("nl_result")
    if result is None:
        return

    if result["status"] != "ok":
        st.warning(result["message"])
    else:
        st.write(result["explanation"]["summary"])

    user_prefs = result["user_prefs"]
    recommendations = result["recommendations"]
    notes_by_song_id = {}
    if result["status"] == "ok":
        notes_by_song_id = {note["song_id"]: note["note"] for note in result["explanation"]["song_notes"]}

    st.subheader(f"Top {len(recommendations)} Recommendations")
    render_confidence(result["confidence"])
    for rank, (song, score, reasons) in enumerate(recommendations, start=1):
        render_recommendation(rank, song, score, reasons, user_prefs)
        note = notes_by_song_id.get(song["id"])
        if note:
            st.caption(note)

    if result["status"] != "ok":
        with st.expander("Raw text table"):
            st.code(result["fallback_table"], language=None)


def main():
    st.set_page_config(page_title="Match ur Mood 2.0", layout="wide")
    st.title("🎵 Match ur Mood 2.0")

    songs = _load_songs_cached(CSV_PATH)
    catalog_genres, catalog_moods = get_catalog_vocabulary(songs)

    guided_tab, nl_tab = st.tabs(["🎛️ Guided Search", "💬 Ask in Plain English"])

    with guided_tab:
        render_guided_search(songs, catalog_genres, catalog_moods)

    with nl_tab:
        render_nl_query(songs)


if __name__ == "__main__":
    main()
