"""Environment-backed application settings."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "pharma.db")))
MAX_QUERY_ROWS = int(os.getenv("MAX_QUERY_ROWS", "200"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
