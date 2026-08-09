"""FastAPI main application entry point for DevMind AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import health, query, repositories
from app.services.rag_service import RAGService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("devmind_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle and initialize single instance of RAGService."""
    logger.info("Initializing RAGService application state...")
    app.state.rag_service = RAGService()
    yield
    logger.info("Shutting down DevMind AI API application...")


app = FastAPI(
    title="DevMind AI API",
    description="Code-aware RAG backend for semantic codebase search and Q&A",
    version="1.0.0",
    lifespan=lifespan,
)

# Register endpoint routers
app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(query.router)
