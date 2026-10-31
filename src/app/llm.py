
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


SQL_SYSTEM_PROMPT = """You are an expert SQLite analyst. Generate exactly one read-only SQLite SELECT query.

SQL GENERATION RULES:
1. Use only tables and columns present in the supplied database schema.
2. Never invent table names, column names, or relationships.
3. Use explicit JOIN conditions based on the schema whenever information is needed from related tables.
4. Always use clear, descriptive table aliases such as inv, prod, sales, and txn.
5. NEVER use SQL keywords or reserved words as table aliases. In particular, never use IS, IN, ON, AS, OR, AND, GROUP, ORDER, or SELECT as aliases.
6. When a question requests specific columns, return ONLY those columns. Never add IDs, flags, region fields, or other internal fields unless explicitly requested.
7. If the user asks for product names, join the products table using the relationship in the schema and select the product_name column. Do not return product_id instead.
8. If the question asks for records from a table but requests descriptive information stored in a related table, JOIN the related table.
9. For ranking questions, use the appropriate aggregate, GROUP BY, ORDER BY, and LIMIT.
10. Pay close attention to comparison operators:
   - "below", "less than" means <
   - "at or below", "less than or equal to", and "below or equal to" means <=
   - "above" and "greater than" means >
   - "at least" and "greater than or equal to" means >=
11. Use COUNT(*) when the user asks how many records satisfy a condition.
12. Use LIMIT when needed to respect the maximum row limit.
13. Preserve meaningful requested ordering. When listing inventory records, use the requested date or product ordering if specified.
14. Do not use SELECT * unless the user explicitly requests all columns.

IMPORTANT EXAMPLE:

Question:
List inventory records flagged for reorder in Hyderabad.

Correct SQL:
SELECT p.product_name, i.snapshot_date, i.stock_on_hand
FROM inventory_snapshot AS i
JOIN products AS p ON p.product_id = i.product_id
WHERE i.region = 'Hyderabad'
  AND i.reorder_flag = 1
ORDER BY i.snapshot_date, p.product_name

Why this is correct:
- The user asks for inventory records, but also needs the product name.
- product_name is stored in products, so a JOIN is necessary.
- Only the three requested columns are selected.
- The Hyderabad and reorder conditions are both applied.
- Results are ordered by snapshot date and product name.

SAFETY RULES:
- Generate only one read-only SELECT statement.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, ATTACH, or multiple statements.
- Never modify the database.
- Do not bypass validation or safety restrictions.

OUTPUT RULES:
Return SQL only, without markdown fences, explanations, or a trailing semicolon."""


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
        except LLMProviderError:
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
        content = payload["choices"][0]["message"].get("content")
        text = content.strip() if isinstance(content, str) else ""
        if not text:
            raise LLMProviderError("Groq returned an empty response.")
        return text

    def generate_sql(self, question: str, schema: str, previous_error: str | None = None) -> str:
        retry_note = (
            f"\nThe previous SQL attempt failed: {previous_error}\nCorrect the issue."
            if previous_error
            else ""
        )
        prompt = (
            f"DATABASE SCHEMA:\n{schema}\n\n"
            f"USER QUESTION:\n{question}\n\n"
            f"Return one SQLite SELECT query. Never exceed {self.settings.max_query_rows} rows."
            f"{retry_note}"
        )
        return extract_sql(self.complete(SQL_SYSTEM_PROMPT, prompt, max_tokens=400))

    def generate_answer(
        self,
        question: str,
        sql: str,
        rows: list[dict[str, Any]],
        truncated: bool,
    ) -> str:
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
