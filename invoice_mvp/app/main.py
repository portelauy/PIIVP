from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router


def create_app() -> FastAPI:
    """Application factory used by ASGI servers (Uvicorn, Vercel, etc.).

    Architectural decision: use a factory to make testing and configuration
    simple while staying compatible with serverless deployments.
    """

    app = FastAPI(title="Invoice Processing MVP", version="0.1.0")

    # Basic CORS for demo UI; tighten in real deployments.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
