"""FastAPI main application entry point for DevMind AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import conversations, health, query, repositories
from app.db.database import Base, engine
from app.services.rag_service import RAGService
from app.utils.config import get_cors_origins

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("devmind_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle and initialize single instance of RAGService."""
    import resource
    import sys

    def _get_rss() -> float:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024

    logger.info("[TELEMETRY stage 1] Process startup (RSS=%.2f MB)", _get_rss())
    logger.info("Initializing RAGService application state...")
    app.state.rag_service = RAGService()

    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Database schema check warning: %s", exc)

    # Recover any pending queued indexing jobs from Redis
    try:
        app.state.rag_service.indexing_coordinator.recover_on_startup()
    except Exception as exc:
        logger.warning("Queue startup recovery notice: %s", exc)

    logger.info("[TELEMETRY stage 2] Application startup complete (RSS=%.2f MB)", _get_rss())
    yield
    logger.info("Shutting down DevMind AI API application (Final RSS=%.2f MB)...", _get_rss())


app = FastAPI(
    title="DevMind AI API",
    description="Code-aware RAG backend for semantic codebase search and Q&A",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS Middleware
origins = get_cors_origins()
logger.info("Configuring CORS middleware with origins: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization", "Accept", "X-Session-ID"],
)

# Register endpoint routers
app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(query.router)
app.include_router(conversations.router)
