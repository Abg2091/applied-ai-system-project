# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.


As a strech feature, I have added a secodary data source: 

Summary: Adding Artist Similarity to a Music Recommender

What's Changing & Why:

The project currently recommends songs using static JSON files for genre and artist notes. This update adds a second data source — an artist similarity database — so the system can also understand queries like "songs like Neon Echo." Crucially, this new source will influence both song scoring and explanations, not just the explanation layer. The old JSON files remain untouched; this is purely additive.

How It Works:

A one-time script reads song data (energy, tempo, mood, etc.), groups songs by artist, and calculates which artists sound most similar to each other. Results are saved into a local SQLite database file.

When a user types a query mentioning a reference artist, the system extracts that artist name (constrained to real artists in the catalog to prevent hallucinations).

That artist is looked up in the similarity database to get a boost map — a ranked list of musically similar artists with weights.

Those weights nudge song scores upward for similar artists and generate a human-readable explanation like "Because you mentioned Neon Echo, this artist is musically similar."

If no reference artist is mentioned, nothing changes — all existing behavior is preserved exactly.

Note: Refer to the snipet "Artist Similarity Output" in the asset forlder for the Streamlit output.
---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked it to add a natural-language layer on top of my recommender, using the Gemini API and RAG (retrieval-augmented generation), so you could type a plain sentence instead of filling in genre/mood/energy by hand. My one hard requirement was that it could never make up a song that isn't actually in my catalog.

**Prompts used:**

- "I am keen on to integrate external documentation retrieval (large song dataset) and automated answer validation into this project using a RAG approach, augmented with testing and guardrails."
- "Analyze the provided music recommender strategy and identify its inherent gaps and shortcomings. Then delineate a step-by-step plan to address each gap. Build a system that is demonstrably simple, robust, reliable, and secure."
- "Yes, proceed with stage [1/2/3/4]." (repeated once per stage, after checking each one's tests passed)
- "Create a mermaid diagram of the revised plan" / "split them into two separate files"

**What did the agent generate or change?**

It built the feature in 4 stages instead of one big change, so each piece could be tested on its own before moving to the next:

- `src/nl_interface.py` — turns free text into a profile, using a schema that only allows real genres/moods from my catalog
- `src/llm_client.py` — the actual Gemini API calls
- `src/retrieval.py` + `data/knowledge/*.json` — short background notes per genre/artist, used to ground the explanations
- `src/guardrails.py` — a second check that scans Gemini's explanation text for any song it shouldn't be mentioning
- A matching test file for each of the above, plus updates to `requirements.txt`, `.gitignore`, and `.env.example`

**What did you verify or fix manually?**

- Ran the full test suite after every stage (56 tests, all passing) instead of waiting until the end.
- Ran the CLI with no API key set, to confirm it falls back to the plain recommender instead of crashing.
- Ran a fake "adversarial" demo where the explanation deliberately named a song outside the recommended list, and confirmed the guardrail actually caught it and printed a "1 of 3 suppressed" summary.
- Double-checked every genre/artist name in my new background-notes files against the real CSV, so there were no typos silently breaking the lookup.

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

<!-- e.g., Strategy, Factory, Observer, etc. -->

**How did AI help you brainstorm or implement it?**

<!-- Describe the conversation or suggestions that led to your decision -->

**How does the pattern appear in your final code?**

<!-- Point to the relevant class or method -->
