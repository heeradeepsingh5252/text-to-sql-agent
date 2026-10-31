"""FastAPI route tests using a temporary database and mocked LLM."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent import TextToSQLAgent
from app.config import Settings
from app.database import create_database
from app.main import create_app


class FakeLLM:
    def generate_sql(self, question, schema, previous_error=None):
        return "SELECT COUNT(*) AS product_count FROM products"

    def generate_answer(self, question, sql, rows, truncated):
        return f"There are {rows[0]['product_count']} products."


def test_health_schema_and_ask(tmp_path: Path) -> None:
    database = create_database(tmp_path / "pharma.db")
    settings = Settings(database_path=database, rate_limit_requests=100)
    agent = TextToSQLAgent(settings, FakeLLM())
    client = TestClient(create_app(settings, agent))

    assert client.get("/health").json()["status"] == "ok"
    assert "TABLE products" in client.get("/schema").json()["schema"]
    response = client.post("/ask", json={"question": "How many products are there?"})
    assert response.status_code == 200
    assert response.json()["rows"] == [{"product_count": 8}]
    assert response.json()["retries"] == 0


def test_ask_validates_question_length(tmp_path: Path) -> None:
    database = create_database(tmp_path / "pharma.db")
    settings = Settings(database_path=database, rate_limit_requests=100)
    client = TestClient(create_app(settings, TextToSQLAgent(settings, FakeLLM())))
    assert client.post("/ask", json={"question": "x"}).status_code == 422


def test_ask_rate_limit_returns_429(tmp_path: Path) -> None:
    database = create_database(tmp_path / "pharma.db")
    settings = Settings(database_path=database, rate_limit_requests=1)
    client = TestClient(create_app(settings, TextToSQLAgent(settings, FakeLLM())))
    assert client.post("/ask", json={"question": "How many products?"}).status_code == 200
    assert client.post("/ask", json={"question": "How many products?"}).status_code == 429


def test_ask_rejects_whitespace_only_question(tmp_path: Path) -> None:
    database = create_database(tmp_path / "pharma.db")
    settings = Settings(database_path=database, rate_limit_requests=100)
    client = TestClient(create_app(settings, TextToSQLAgent(settings, FakeLLM())))
    assert client.post("/ask", json={"question": "   "}).status_code == 422
