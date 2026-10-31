"""Tests for orchestration and retry behavior with a mocked LLM."""
from pathlib import Path

import pytest

from app.agent import AgentQueryError, TextToSQLAgent
from app.config import Settings
from app.database import create_database


class FakeLLM:
    def __init__(self, sql_responses):
        self.sql_responses = list(sql_responses)
        self.errors = []

    def generate_sql(self, question, schema, previous_error=None):
        self.errors.append(previous_error)
        return self.sql_responses.pop(0)

    def generate_answer(self, question, sql, rows, truncated):
        return f"Found {len(rows)} rows for: {question}"


@pytest.fixture()
def database_path(tmp_path: Path) -> Path:
    return create_database(tmp_path / "pharma.db")


def test_agent_runs_valid_query(database_path: Path) -> None:
    llm = FakeLLM(["SELECT COUNT(*) AS n FROM products"])
    agent = TextToSQLAgent(Settings(database_path=database_path), llm)
    result = agent.ask("How many products are listed?")
    assert result.rows == [{"n": 8}]
    assert result.retries == 0
    assert "Found 1 rows" in result.answer


def test_agent_retries_after_unsafe_sql(database_path: Path) -> None:
    llm = FakeLLM(["DROP TABLE products", "SELECT COUNT(*) AS n FROM products"])
    agent = TextToSQLAgent(Settings(database_path=database_path), llm)
    result = agent.ask("How many products are listed?")
    assert result.retries == 1
    assert llm.errors[1]
    assert result.rows == [{"n": 8}]


def test_agent_stops_after_two_retries(database_path: Path) -> None:
    llm = FakeLLM(["DROP TABLE products"] * 3)
    agent = TextToSQLAgent(Settings(database_path=database_path), llm)
    with pytest.raises(AgentQueryError, match="after 3 attempts"):
        agent.ask("Delete all records")
