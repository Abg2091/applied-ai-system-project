# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked it to add a natural-language layer on top of my recommender, using the Claude API and RAG (retrieval-augmented generation), so you could type a plain sentence instead of filling in genre/mood/energy by hand. My one hard requirement was that it could never make up a song that isn't actually in my catalog.

**Prompts used:**

- "I am keen on to integrate external documentation retrieval (large song dataset) and automated answer validation into this project using a RAG approach, augmented with testing and guardrails."
- "Analyze the provided music recommender strategy and identify its inherent gaps and shortcomings. Then delineate a step-by-step plan to address each gap. Build a system that is demonstrably simple, robust, reliable, and secure."
- "Yes, proceed with stage [1/2/3/4]." (repeated once per stage, after checking each one's tests passed)
- "Create a mermaid diagram of the revised plan" / "split them into two separate files"

**What did the agent generate or change?**

It built the feature in 4 stages instead of one big change, so each piece could be tested on its own before moving to the next:

- `src/nl_interface.py` — turns free text into a profile, using a schema that only allows real genres/moods from my catalog
- `src/llm_client.py` — the actual Claude API calls
- `src/retrieval.py` + `data/knowledge/*.json` — short background notes per genre/artist, used to ground the explanations
- `src/guardrails.py` — a second check that scans Claude's explanation text for any song it shouldn't be mentioning
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
