import json

from src.llm_client import (
    EXPLANATION_MAX_TOKENS,
    EXTRACTION_MAX_TOKENS,
    MODEL,
    explain_recommendations,
    extract_profile,
    get_client,
)


class FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeBlock(text)]


class FakeMessages:
    def __init__(self, response_text):
        self._response_text = response_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self._response_text)


class FakeClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_extract_profile_parses_json_response_from_client():
    schema = {"type": "object", "properties": {"genre": {"type": "string"}}}
    response_json = json.dumps(
        {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}
    )
    client = FakeClient(response_json)

    profile = extract_profile(client, "system prompt", "chill lofi please", schema)

    assert profile == {"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True}


def test_extract_profile_sends_expected_model_max_tokens_and_schema():
    schema = {"type": "object", "properties": {}}
    client = FakeClient(
        json.dumps({"genre": "pop", "mood": "happy", "energy": 0.5, "likes_acoustic": None})
    )

    extract_profile(client, "system prompt", "some query", schema)

    call = client.messages.calls[0]
    assert call["model"] == MODEL
    assert call["max_tokens"] == EXTRACTION_MAX_TOKENS
    assert call["system"] == "system prompt"
    assert call["output_config"]["format"]["schema"] is schema
    assert "some query" in call["messages"][0]["content"]


def test_explain_recommendations_parses_json_response_from_client():
    schema = {"type": "object", "properties": {}}
    response_json = json.dumps(
        {"summary": "Here you go", "song_notes": [{"song_id": 1, "note": "matches your mood"}]}
    )
    client = FakeClient(response_json)

    explanation = explain_recommendations(client, "system prompt", "user content", schema)

    assert explanation["summary"] == "Here you go"
    assert explanation["song_notes"][0]["song_id"] == 1


def test_explain_recommendations_sends_expected_model_and_max_tokens():
    schema = {"type": "object", "properties": {}}
    client = FakeClient(json.dumps({"summary": "x", "song_notes": []}))

    explain_recommendations(client, "system prompt", "user content", schema)

    call = client.messages.calls[0]
    assert call["model"] == MODEL
    assert call["max_tokens"] == EXPLANATION_MAX_TOKENS
    assert call["output_config"]["format"]["schema"] is schema


def test_get_client_raises_clear_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    try:
        get_client()
        assert False, "expected RuntimeError when ANTHROPIC_API_KEY is unset"
    except RuntimeError as e:
        assert "ANTHROPIC_API_KEY" in str(e)
