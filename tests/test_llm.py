"""Tests for provider response parsing and SQL code-fence extraction."""
import httpx
import pytest

from app.config import Settings
from app.llm import LLMClient, LLMConfigurationError, LLMProviderError, extract_sql


def test_extract_sql_from_markdown_fence() -> None:
    assert extract_sql("```sql\nSELECT 1;\n```") == "SELECT 1"


def test_extract_sql_rejects_multiple_code_blocks() -> None:
    with pytest.raises(LLMProviderError):
        extract_sql("```sql\nSELECT 1\n```\n```sql\nSELECT 2\n```")


def test_missing_api_key_fails_clearly() -> None:
    client = LLMClient(Settings(provider="gemini", api_key=""))
    with pytest.raises(LLMConfigurationError, match="LLM_API_KEY"):
        client.complete("system", "user")


def test_gemini_request_is_made_with_expected_payload(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        is_error = False
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "SELECT 1"}]}}]}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = LLMClient(Settings(provider="gemini", api_key="fake-key", model="gemini-test"))
    assert client.complete("system", "user") == "SELECT 1"
    assert "gemini-test:generateContent" in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "fake-key"
    assert "systemInstruction" in captured["json"]


def test_groq_request_is_made_with_expected_payload(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        is_error = False
        def json(self):
            return {"choices": [{"message": {"content": "SELECT 2"}}]}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = LLMClient(Settings(provider="groq", api_key="fake-key", model="llama-test"))
    assert client.complete("system", "user") == "SELECT 2"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
