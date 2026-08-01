"""
Thin wrapper around the Claude API (Stage 1 of the RAG plan).

Both functions here take the API client as a parameter (dependency injection)
so tests can substitute a fake client instead of hitting the network, and
both take a pre-built JSON schema rather than constructing one themselves -
schema/prompt construction lives in src/nl_interface.py where it's testable
without any network access (see build_extraction_schema and
build_explanation_schema).

Structured output (`output_config.format`) is the primary anti-hallucination
guardrail: the explanation schema's song references are enum-constrained to
the exact candidate IDs handed in, so Claude cannot name a song outside that
set - there's no other value the schema will accept.

Reliability note: this stage deliberately does NOT catch API errors - that's
Stage 2's job. A transient failure here should surface, not be silently
swallowed, until the fallback path exists to catch it.
"""

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-5"
EXTRACTION_MAX_TOKENS = 256
EXPLANATION_MAX_TOKENS = 512


def get_client():
    """Builds an Anthropic client, resolving ANTHROPIC_API_KEY from the
    environment (including a local .env file via load_dotenv() above).
    Never log or print the key itself - only whether it was found.
    """
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return anthropic.Anthropic()


def _first_text_block(response) -> str:
    return next(block.text for block in response.content if block.type == "text")


def extract_profile(client: Any, system_prompt: str, user_query: str, schema: Dict) -> Dict:
    """One Claude call: free text -> a profile dict matching `schema`.

    `schema` should come from nl_interface.build_extraction_schema(), which
    enum-constrains genre/mood to the catalog's real vocabulary.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=EXTRACTION_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": f"user_query: {user_query}"}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    return json.loads(_first_text_block(response))


def explain_recommendations(
    client: Any, system_prompt: str, user_content: str, schema: Dict
) -> Dict:
    """One Claude call: recommendation context -> a grounded explanation dict.

    `schema` should come from nl_interface.build_explanation_schema(), which
    enum-constrains any song reference to the exact recommended IDs.
    `user_content` should come from nl_interface.format_candidates_for_prompt(),
    which lists only the actual recommend_songs() output plus any grounding
    notes - never anything Claude itself introduced.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=EXPLANATION_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    return json.loads(_first_text_block(response))
