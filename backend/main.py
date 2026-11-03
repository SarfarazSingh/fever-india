"""ASGI entrypoint used by `uvicorn main:app` and Vercel's FastAPI runtime."""

from app.main import app

__all__ = ["app"]
