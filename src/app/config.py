"""Centralized environment-backed application settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # .env support is optional when environment variables are set directly.
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    provider: str = "gemini"
    api_key: str = ""
    model: str = ""
    database_path: Path = PROJECT_ROOT / "data" / "pharma.db"
    max_query_rows: int = 200
    allowed_origins: tuple[str, ...] = ("http://localhost:5173",)
    query_timeout_seconds: float = 3.0
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60
    max_output_tokens: int = 500

    @classmethod
    def from_env(cls) -> "Settings":
        raw_path = Path(os.getenv("DATABASE_PATH", "data/pharma.db")).expanduser()
        database_path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        origins = tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        )
        return cls(
            provider=os.getenv("LLM_PROVIDER", "gemini").strip().lower(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            model=os.getenv("LLM_MODEL", "").strip(),
            database_path=database_path.resolve(),
            max_query_rows=max(1, min(int(os.getenv("MAX_QUERY_ROWS", "200")), 5000)),
            allowed_origins=origins,
            query_timeout_seconds=max(0.1, float(os.getenv("QUERY_TIMEOUT_SECONDS", "3"))),
            rate_limit_requests=max(1, int(os.getenv("RATE_LIMIT_REQUESTS", "20"))),
            rate_limit_window_seconds=max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))),
            max_output_tokens=max(100, min(int(os.getenv("MAX_OUTPUT_TOKENS", "500")), 2000)),
        )

    @property
    def effective_model(self) -> str:
        if self.model:
            return self.model
        defaults = {
            "gemini": "gemini-3.8-flash",
            "groq": "openai/gpt-oss-20b",
        }
        return defaults.get(self.provider, "")
