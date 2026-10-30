"""Minimal FastAPI application scaffold; query endpoints are added later."""

from fastapi import FastAPI

app = FastAPI(
    title="Pharma Text-to-SQL Agent",
    description="A schema-aware, read-only analytics assistant for a synthetic pharma database.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a small health response for local development and deployment checks."""
    return {"status": "ok"}
