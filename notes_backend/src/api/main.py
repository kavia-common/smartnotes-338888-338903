from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.db import create_engine, create_sessionmaker
from src.api.errors import ApiException, api_exception_handler
from src.api.routers.notes import router as notes_router
from src.api.routers.tags import router as tags_router
from src.api.settings import Settings, get_settings

logger = logging.getLogger("smartnotes.api")

openapi_tags: List[dict] = [
    {"name": "health", "description": "Health and diagnostics endpoints."},
    {"name": "notes", "description": "Create, read, update, delete, search/filter notes and pin/unpin."},
    {"name": "tags", "description": "Create, read, update, delete tags."},
]


def _build_app(settings: Settings) -> FastAPI:
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)

    app = FastAPI(
        title="SmartNotes API",
        description="Backend REST API for SmartNotes (notes, tags, search/filter, pin/unpin).",
        version="1.0.0",
        openapi_tags=openapi_tags,
    )

    app.add_exception_handler(ApiException, api_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dependency injection: make a single sessionmaker available to all routes
    async def _sessionmaker_dep() -> async_sessionmaker[AsyncSession]:
        return sessionmaker

    app.dependency_overrides[async_sessionmaker[AsyncSession]] = _sessionmaker_dep  # type: ignore[index]

    @app.get(
        "/",
        tags=["health"],
        summary="Health check",
        description="Simple health check endpoint.",
        operation_id="health_check",
    )
    async def health_check() -> dict:
        """PUBLIC_INTERFACE Health check endpoint."""
        return {"message": "Healthy"}

    app.include_router(notes_router)
    app.include_router(tags_router)

    return app


settings = get_settings()
app = _build_app(settings)
