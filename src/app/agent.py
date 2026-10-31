"""Orchestrate schema-aware SQL generation, validation, retries and answers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings
from app.executor import QueryExecutionError, execute_read_only
from app.llm import LLMClient
from app.schema import get_schema_description
from app.sql_guard import validate_select_only


class TextToSQLClient(Protocol):
    def generate_sql(self, question: str, schema: str, previous_error: str | None = None) -> str: ...
    def generate_answer(self, question: str, sql: str, rows: list[dict[str, Any]], truncated: bool) -> str: ...


@dataclass(frozen=True)
class AgentResult:
    question: str
    sql: str
    answer: str
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    retries: int


class AgentQueryError(RuntimeError):
    def __init__(self, message: str, retries: int):
        super().__init__(message)
        self.retries = retries


class TextToSQLAgent:
    def __init__(
        self,
        settings: Settings,
        llm_client: TextToSQLClient | None = None,
    ):
        self.settings = settings
        self.llm = llm_client or LLMClient(settings)

    def ask(self, question: str) -> AgentResult:
        schema = get_schema_description(self.settings.database_path, sample_rows=0)
        last_error = ""
        max_attempts = 3  # first attempt plus at most two retries

        for attempt in range(max_attempts):
            try:
                generated_sql = self.llm.generate_sql(question, schema, last_error or None)
                validation = validate_select_only(generated_sql, self.settings.max_query_rows)
                if not validation.valid or not validation.sql:
                    last_error = validation.error or "SQL validation failed"
                    continue
                rows, truncated = execute_read_only(
                    validation.sql,
                    self.settings.database_path,
                    max_rows=self.settings.max_query_rows,
                    timeout_seconds=self.settings.query_timeout_seconds,
                )
                answer = self.llm.generate_answer(question, validation.sql, rows, truncated)
                if truncated:
                    answer = (
                        f"{answer}\n\nNote: results are capped at "
                        f"{self.settings.max_query_rows} rows."
                    )
                return AgentResult(
                    question=question,
                    sql=validation.sql,
                    answer=answer,
                    rows=rows,
                    row_count=len(rows),
                    truncated=truncated,
                    retries=attempt,
                )
            except QueryExecutionError as error:
                last_error = str(error)

        raise AgentQueryError(f"Could not produce a safe, executable query after {max_attempts} attempts. Last error: {last_error}", retries=2)
