# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

This model will be called as "Match ur Mood 2.0"

(Bumped from 1.0 — this update matches the name already shown in the
Streamlit app and reflects what's new: a much bigger catalog, confidence
scoring, and a browser UI.)

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

"Match ur Mood" music recommender is intended to find a list of top 5 songs from the database to that synchronize with user's mood. 

Prompts:  

- What kind of recommendations does it generate  

It generates mood based recommendation over genre.

- What assumptions does it make about the user  

It assumes that the mood correlates directly with the energy/feel a user is actually asking for in the moment, so it's a more reliable predictor of "will this song feel right right now."

- Is this for real users or classroom exploration  

Match ur Mood 2.0 is currently in its first phase so I would called it as more of a classroom exploration than real user ready product.

It can now be used either from the command line (`python -m src.main`) or from a browser, via the new Streamlit app (`streamlit run src/streamlit_app.py`) — same recommender underneath, just a friendlier way in for someone who doesn't want to touch a terminal.

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  

Freature used are: Mood, genre, energy and acousticness.

- What user preferences are considered  

Apart from regular preference, 5 adversarial user preferances such as conflicting preferences, values absent from the catalog, out-of-range inputs, Artist-loyalty overload,and messy string casing were considered to test the system.

- How does the model turn those into a score  

To score a song, the "Recommender" adds up points for every way it matches what the user asked for, but not all matches count equally. Mood and energy are weighted the heaviest on purpose, because my philosophy is to match user's mood in the moment, not lock onto a fixed identity.

- What changes did you make from the starter logic  

The significant change that I made is, mood and energy are weighted the heaviest on purpose, in order to match user's mood in the moment.

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

- What's new: confidence scoring

Alongside every set of recommendations, the system now also works out how confident it is in that answer — not by asking an AI to guess, but by calculating it from the same kind of hard facts the scoring already uses: did the results actually match the genre/mood asked for, and how strong is the single best match compared to the best it could possibly be. It comes out as a simple low/medium/high label plus a short reason.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  

There are total 125 songs in the catalog.

- What genres or moods are represented  

Genres in the catalog (48 unique):
pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, hip hop, folk, metal, R&B, country, EDM, reggae, blues, techno, funk, punk, disco, gospel, k-pop, latin, bossa nova, house, dubstep, soul, chiptune, orchestral, afrobeat, salsa, flamenco, celtic, trip hop, drum and bass, grunge, ska, opera, bluegrass, indie folk, dream pop, garage rock, math rock, vaporwave, chillstep, new age, samba, tango.

Moods in the catalog (32 unique):
happy, chill, intense, relaxed, moody, focused, melancholic, triumphant, nostalgic, aggressive, romantic, hopeful, euphoric, playful, somber, mysterious, confident, dark, dramatic, dreamy, energetic, epic, furious, hypnotic, intricate, peaceful, quirky, raw, restless, sensual, soulful, warm.

- Did you add or remove data  

I added 13 new songs early on to fill genre/mood gaps in the original data, and this session added 102 more songs, bringing the catalog from 23 to 125 total. The goal of the big second addition was the same as the first, just at a much bigger scale — more genres and moods actually have real songs behind them, so more kinds of requests get a genuine match instead of a fallback.

- Are there parts of musical taste missing in the dataset  

The original gaps (reggae, techno, EDM, classical, folk, metal, and moods like somber, playful, euphoric, mysterious) were filled in earlier. This session added a lot more variety on top — funk, punk, disco, gospel, k-pop, latin, house, dubstep, soul, and several "world"/orchestral-adjacent styles — so the catalog now covers a much wider slice of popular and electronic music. Still missing: anything outside English-language, Western-leaning music (no regional or non-English genres), and a handful of moods (dramatic, epic, hypnotic, intricate, quirky, raw, sensual, soulful) still exist on only a single song each, so requests for those are still thin.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  

User with simple preferences (mood, energy, genre, and acousticness). 

- Any patterns you think your scoring captures correctly  

Mood matching is the pattern I believe the scoring captures correctly.

- Cases where the recommendations matched your intuition  

During the experiment of weight shift for genre and energy.

- What's new: transparency about weak matches

The new confidence score means a user now gets a signal when a result is weak, instead of it failing silently. This matters most for a rare genre/mood request that used to come back looking like any other recommendation, with nothing telling the user "this is just the closest thing available, not a real match."

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Rare-tag starvation: Some moods/genres only exist on one song, so users asking for those get almost no real choice. This session's catalog expansion (23 → 125 songs) mostly fixed this for genres, but moods are only partly improved:

- Genres: 0 of 48 genres now have only 1 song (every genre has at least 2) — this is essentially solved.
- Moods: 8 of 32 moods still have only 1 song: dramatic, epic, hypnotic, intricate, quirky, raw, sensual, soulful. Fuzzy mood matching would still help close this last gap.

Note: confidence scoring (added this session) does not fix rare-tag starvation — it's a diagnostic, not a cure. What it does is make a weak match visible (as "low confidence") instead of silently returning it looking just as solid as a real match.

Prompts:  

- Features it does not consider 

Song data columns that scoring ignores entirely are tempo_bpm, valence, danceability, and artist/title (only used for the diversity cap, not for matching taste).

Also missing from the model itself:

No listening history or collaborative signal — every recommendation is a one-shot match against a static profile; nothing learns from what the user actually played/skipped/liked before.

No negative preferences choice. e.g. a user can say what genre/mood/energy they want, but can't say what to avoid.

No popularity, recency, or lyrical/cultural content — release date, trending status, language, or explicit content aren't modeled at all.


- Genres or moods that are underrepresented  

Counting occurrences across all 125 songs (updated this session — was 23 songs, 12 of 17 genres and 10 of 16 moods single-song, before the catalog expansion):

Genres — 0 of 48 appear in only 1 song. Every genre now has at least 2 songs, most have 2-4, and one (lofi) has 6 — no more single points of failure.

Moods — 8 of 32 appear in only 1 song (single point of failure):
dramatic, epic, hypnotic, intricate, quirky, raw, sensual, soulful.

- Cases where the system overfits to one preference 

In the cases where the energy weightage doubled, in the absence of other feature match, the high energy points single handedly outscore the other recommendations with low energy points.

- Ways the scoring might unintentionally favor some users  

Songs and user profiles with exact mood and energy match.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  

Adversarial Profiles Tested:

"Conflicting mood vs. energy (wants melancholic AND high-energy)",
 {"genre": "classical", "mood": "melancholic", "energy": 0.9, "likes_acoustic": True},
        
"Genre & mood that don't exist in the catalog at all",
{"genre": "opera", "mood": "furious", "energy": 0.5},
        
"Out-of-range target energy (1.4, above the natural 0-1 scale)",
{"genre": "techno", "mood": "mysterious", "energy": 1.4, "likes_acoustic": False},
        
"Messy case/whitespace in genre & mood",
{"genre": "  PoP ", "mood": "HAPPY", "energy": 0.8, "likes_acoustic": None},
        
"Artist-loyalty overload (LoRoom dominates lofi/chill matches)",
{"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}


- What you looked for in the recommendations  

I mainly looked for the mood and the energy of the user in the current state and used genre as the tie breaker in the recommendation process.

- What surprised you  

The thing that really surprised me is that how the size of the data set determines the limitaions of the system.

- Any simple tests or comparisons you ran  

Before vs. After: what changed when energy started counting for more and genre for less

When a song already nailed both genre AND mood, nothing dethroned it. Winter Sonata (classical/melancholic), Hidden Frequencies (techno/mysterious), and Half Light (indie pop/relaxed) all stayed in 1st place before and after. A double exact-match is still hard to beat even with genre weakened, because mood alone is still worth 2 points.

Songs that only matched on genre (not mood) got shakier. In the "acoustic fence-sitter" test, Rooftop Lights held 3rd place before purely on its genre match. After the change, that genre match was worth less, and it got bumped out of the top spots by songs like Focus Flow, Midnight Coding, and Velvet Whisper — songs with no genre match at all, but whose energy level was simply closer to what the user asked for. In plain terms: being "close to the right vibe" now beats being "the right genre" more often than it used to.

When nothing matched genre or mood anyway, the whole list just got bigger scores, same order. In the "made-up genre/mood" test (opera/furious) and the "messy case" test (PoP/HAPPY), scores roughly doubled across the board, but the ranking of songs didn't move at all — because every song there was competing purely on energy, so everyone got the same boost.

The biggest shake-up was the deliberately "confused" profile (wants a sad, quiet mood and a high-energy song at the same time). Before, a few in-between songs (Dirt Road Sunrise, Coffee Shop Stories) squeaked into the top 5 on modest overall scores. After the change, they got pushed out entirely, replaced by loud, high-energy tracks (Storm Runner, Gym Hero, Sunrise City) that don't fit the mood at all but happen to match the energy target almost exactly. This is the clearest sign of the shift: when genre/mood can't settle the argument, energy now wins the tie-break much more decisively.

Bottom line: the system got more "vibe-driven" and less "genre-loyal." If two songs are otherwise close, the one that feels like the right energy level now has a much better shot at winning, even over one that's technically the right genre. That's good if users care more about mood/energy than genre labels — but it means genre fans (e.g., someone who specifically wants jazz) will more easily see off-genre songs creep into their recommendations if those songs happen to have the right energy.

No need for numeric metrics unless you created some.

- What's new: automated tests, and checking the confidence scores

Besides the manual adversarial-profile testing above, this session added an automated test suite — 112 tests across `tests/`, covering the core recommender, the natural-language layer, the retrieval/grounding notes (now two independent sources: the original genre/artist JSON notes, plus a SQLite-backed artist-similarity graph that also feeds scoring when a query names a reference artist), the safety guardrails, and the new confidence scoring — so these behaviors get checked automatically instead of only by hand.

I also specifically checked the confidence score against a few known scenarios: a strong genre/mood match scored about 0.83 ("high"); a rare-tag request (genre and mood each only on a couple of songs) scored about 0.51 ("medium"); a genre/mood that doesn't exist in the catalog at all scored about 0.22 ("low"); and a request with no genre/mood preference at all (energy only) correctly still scored about 0.82 ("high") — it wasn't penalized just for not stating a preference it never made.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  

Use of valence and danceability (loaded by load_songs but never scored). Add a target_valence or wants_danceable preference the same way target_energy/likes_acoustic work now, so users can say "upbeat and danceable" independent of raw energy.

- Better ways to explain recommendations  

Right now explain_recommendation only lists reasons that cleared a threshold (e.g. energy_closeness > 0.85), so a song scored mostly on energy with no reason text still says "closest overall match available" which is uninformative. Use of the score_breakdown dict (already computed in src/recommender.py:196) to always show the dominant contributor by name and magnitude, e.g. "mainly recommended for its energy match (+2.8 of 4.4 points)," even when it's below the current reason-text cutoff.

- Improving diversity among the top results  

Currently select_diverse_top_k only caps by artist — a user can still get 5 songs that are all the same genre+mood if MAX_SONGS_PER_ARTIST allows it. Extend the diversity cap to also limit repeats of genre or mood in the top-k (e.g. max 2 per genre), so a "lofi/chill" fan still sees some variety instead of a wall of near-identical tracks.

- Handling more complex user tastes  

The model assumes one favorite genre/mood/energy per user, but real tastes are contextual ("chill lofi for studying, high-energy EDM for the gym"). Let UserProfile/user_prefs accept a list of weighted preference profiles and score each song against whichever profile fits best, rather than forcing every song through a single fixed target.

- Extending confidence scoring

Right now confidence is one score for the whole set of recommendations. A natural next step is scoring confidence per song instead, so a user could see that song #1 is a strong match while #4 and #5 are weaker fallbacks, rather than one blended number for the whole list. It would also be worth using a low-confidence result to actively suggest the user try a broader or different request, instead of just labeling it "low" and leaving it there. The weights in the confidence formula (0.6/0.4 for the deterministic score, 0.55/0.25/0.20 for the natural-language version) were hand-picked based on a few worked examples — calibrating them against real user feedback would make the labels more trustworthy.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems 

I got to learn the logic behind the song recommendations from the music app. How they score the song against the user preferences and comapred througg the data base of songs to hand the top most recommendations.

- Something unexpected or interesting you discovered  

The interesting fact that I discovered is the huge size and feature rich data set tends to provide the most accurate recommendation to the users' given preferences.

- How this changed the way you think about music recommendation apps  

This project forced me to think deeply about the possible ways to get the closest match to the users' preferences and faced systems' increasing complexity on the route.

- What's new: building confidence scoring, and revisiting the data gap

Designing the confidence score taught me that "how sure is the AI" doesn't have to mean asking an AI to guess — I could calculate it the same deterministic way as the recommendations themselves, from real signals like whether the genre/mood actually matched. That felt more trustworthy than an LLM self-rating its own certainty, which I read is generally poorly calibrated anyway. Recomputing the rare-tag stats after growing the catalog to 125 songs was also a good lesson: a much bigger dataset basically solved the genre gap (0 of 48 genres single-song now) but barely dented the mood gap (still 8 of 32 moods single-song) — more data helps, but only if it's spread across the dimension that's actually thin.
