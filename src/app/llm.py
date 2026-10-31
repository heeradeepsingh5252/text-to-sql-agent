"""Small HTTP-only adapters for Gemini and Groq. Tests mock HTTP; no SDK is needed."""
from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import Settings


class LLMConfigurationError(RuntimeError):
    """Raised when an LLM provider is not configured."""


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider cannot return a response."""


SQL_SYSTEM_PROMPT = """You are a careful SQLite analyst. Generate exactly one read-only SQL SELECT query.
Use only tables and columns present in the supplied schema. Never use INSERT, UPDATE,
DELETE, DROP, ALTER, CREATE, PRAGMA, ATTACH, or multiple statements. Do not invent columns.
Return SQL only, without markdown fences or explanations. Do not add a semicolon."""

ANSWER_SYSTEM_PROMPT = """You are a concise business analytics assistant. Answer the user's question using
only the supplied SQL result rows. Do not invent facts or calculations not supported by the
rows. State when no rows were returned. Mention when the result was truncated."""


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _ensure_configured(self) -> None:
        if self.settings.provider not in {"gemini", "groq"}:
            raise LLMConfigurationError("LLM_PROVIDER must be either 'gemini' or 'groq'.")
        if not self.settings.api_key:
            raise LLMConfigurationError(
                "LLM_API_KEY is missing. Add your Gemini or Groq API key to the local .env file."
            )
        if not self.settings.effective_model:
            raise LLMConfigurationError("LLM_MODEL is missing for the selected provider.")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        self._ensure_configured()
        token_limit = max_tokens or self.settings.max_output_tokens
        try:
            if self.settings.provider == "gemini":
                return self._gemini_complete(system_prompt, user_prompt, token_limit)
            return self._groq_complete(system_prompt, user_prompt, token_limit)
        except LLMConfigurationError:
            raise
        except httpx.HTTPError as error:
            raise LLMProviderError(f"LLM network request failed: {error}") from error
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMProviderError(f"LLM returned an unexpected response: {error}") from error

    def _gemini_complete(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.effective_model}:generateContent"
        )
        response = httpx.post(
            url,
            headers={"x-goog-api-key": self.settings.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
            },
            timeout=30.0,
        )
        if response.is_error:
            raise LLMProviderError(f"Gemini API error {response.status_code}: {response.text[:500]}")
        payload = response.json()
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise LLMProviderError("Gemini returned an empty response.")
        return text

    def _groq_complete(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json={
                "model": self.settings.effective_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_completion_tokens": max_tokens,
            },
            timeout=30.0,
        )
        if response.is_error:
            raise LLMProviderError(f"Groq API error {response.status_code}: {response.text[:500]}")
        payload = response.json()
        text = payload["choices"][0]["message"]["content"].strip()
        if not text:
            raise LLMProviderError("Groq returned an empty response.")
        return text

    def generate_sql(self, question: str, schema: str, previous_error: str | None = None) -> str:
        retry_note = f"\nThe previous SQL attempt failed: {previous_error}\nCorrect the issue." if previous_error else ""
        prompt = (
            f"DATABASE SCHEMA:\n{schema}\n\n"
            f"USER QUESTION:\n{question}\n\n"
            f"Return one SQLite SELECT query. Never exceed {self.settings.max_query_rows} rows."
            f"{retry_note}"
        )
        return extract_sql(self.complete(SQL_SYSTEM_PROMPT, prompt, max_tokens=400))

    def generate_answer(self, question: str, sql: str, rows: list[dict[str, Any]], truncated: bool) -> str:
        prompt = (
            f"QUESTION: {question}\n\nSQL USED:\n{sql}\n\n"
            f"RESULT ROWS (JSON):\n{rows[:100]}\n\n"
            f"TOTAL ROWS RETURNED: {len(rows)}\nTRUNCATED: {truncated}"
        )
        return self.complete(ANSWER_SYSTEM_PROMPT, prompt, max_tokens=350)


def extract_sql(response_text: str) -> str:
    """Extract one SQL code block if present; otherwise return trimmed text."""
    text = response_text.strip()
    fenced = re.findall(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if len(fenced) > 1:
        raise LLMProviderError("LLM returned more than one SQL code block.")
    if fenced:
        text = fenced[0].strip()
    if not text:
        raise LLMProviderError("LLM returned empty SQL.")
    return text.rstrip().rstrip(";").strip()
