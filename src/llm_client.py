"""
Thin wrapper around the Gemini API (originally built against Claude; swapped
to Google Gemini - see the provider-swap plan).

Both functions here take the API client as a parameter (dependency injection)
so tests can substitute a fake client instead of hitting the network, and
both take a pre-built JSON schema rather than constructing one themselves -
schema/prompt construction lives in src/nl_interface.py where it's testable
without any network access (see build_extraction_schema and
build_explanation_schema). Those schemas are passed through unchanged: we
use Gemini's `response_json_schema` config field specifically because it
accepts a raw JSON Schema dict (lowercase types, `enum`, nested objects) -
the same shape the schema builders already produce for structured output.

Structured output is the primary anti-hallucination guardrail: the
explanation schema's song references are enum-constrained to the exact
candidate IDs handed in, so Gemini cannot name a song outside that set -
there's no other value the schema will accept.

Reliability note: this stage deliberately does NOT catch API errors - that's
nl_interface.py's job (see run_nl_query's llm_errors tuple). A transient
failure here should surface, not be silently swallowed, until the fallback
path exists to catch it.
"""

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.5-flash"
EXTRACTION_MAX_TOKENS = 256
EXPLANATION_MAX_TOKENS = 512


def get_client():
    """Builds a Gemini client, resolving GEMINI_API_KEY from the environment
    (including a local .env file via load_dotenv() above). Never log or
    print the key itself - only whether it was found.
    """
    from google import genai

    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return genai.Client()


def _generate_json(client: Any, system_prompt: str, contents: str, schema: Dict, max_tokens: int) -> Dict:
    from google.genai import types

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=schema,
            max_output_tokens=max_tokens,
            # Gemini 3.5 Flash has thinking enabled by default, and on a
            # short structured-output call the model can spend the entire
            # max_output_tokens budget on internal thinking, hitting
            # MAX_TOKENS with empty visible text before writing any JSON.
            # Neither task here needs deep reasoning, so disable it outright.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return json.loads(response.text)


def extract_profile(client: Any, system_prompt: str, user_query: str, schema: Dict) -> Dict:
    """One Gemini call: free text -> a profile dict matching `schema`.

    `schema` should come from nl_interface.build_extraction_schema(), which
    enum-constrains genre/mood to the catalog's real vocabulary.
    """
    return _generate_json(
        client, system_prompt, f"user_query: {user_query}", schema, EXTRACTION_MAX_TOKENS
    )


def explain_recommendations(
    client: Any, system_prompt: str, user_content: str, schema: Dict
) -> Dict:
    """One Gemini call: recommendation context -> a grounded explanation dict.

    `schema` should come from nl_interface.build_explanation_schema(), which
    enum-constrains any song reference to the exact recommended IDs.
    `user_content` should come from nl_interface.format_candidates_for_prompt(),
    which lists only the actual recommend_songs() output plus any grounding
    notes - never anything Gemini itself introduced.
    """
    return _generate_json(
        client, system_prompt, user_content, schema, EXPLANATION_MAX_TOKENS
    )
