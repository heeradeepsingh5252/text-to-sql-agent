"""FastAPI application exposing health, schema and natural-language query routes."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.agent import AgentQueryError, TextToSQLAgent
from app.config import Settings
from app.llm import LLMConfigurationError, LLMProviderError
from app.rate_limit import RateLimiter
from app.schema import get_schema_description


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Question must contain at least 3 non-whitespace characters")
        return cleaned


class AskResponse(BaseModel):
    question: str
    sql: str
    answer: str
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    retries: int


def create_app(
    settings: Settings | None = None,
    agent: TextToSQLAgent | None = None,
) -> FastAPI:
    configured = settings or Settings.from_env()
    query_agent = agent or TextToSQLAgent(configured)
    limiter = RateLimiter(configured.rate_limit_requests, configured.rate_limit_window_seconds)

    application = FastAPI(
        title="Pharma Text-to-SQL Agent",
        description=(
            "A schema-aware natural-language analytics API for a synthetic pharma database. "
            "Only parser-validated, read-only SQLite SELECT queries are executed."
        ),
        version="1.0.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(configured.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.middleware("http")
    async def enforce_rate_limit(request: Request, call_next):
        if request.url.path == "/ask" and request.method == "POST":
            client_host = request.client.host if request.client else "unknown"
            if not limiter.allow(client_host):
                return await _rate_limit_response()
        return await call_next(request)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "database_exists": configured.database_path.is_file(),
            "provider": configured.provider,
        }

    @application.get("/schema", tags=["database"])
    def schema() -> dict[str, str]:
        try:
            return {"schema": get_schema_description(configured.database_path, sample_rows=2)}
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @application.post("/ask", response_model=AskResponse, tags=["query"])
    def ask(payload: AskRequest) -> AskResponse:
        try:
            result = query_agent.ask(payload.question.strip())
            return AskResponse(
                question=result.question,
                sql=result.sql,
                answer=result.answer,
                rows=result.rows,
                row_count=result.row_count,
                truncated=result.truncated,
                retries=result.retries,
            )
        except LLMConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except LLMProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except AgentQueryError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return application


async def _rate_limit_response():
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})


app = create_app()
