#!/bin/bash
set -e

echo "[DevMind-AI] Starting application container..."

echo "[DevMind-AI] Running Alembic database migrations..."
alembic upgrade head

echo "[DevMind-AI] Alembic migrations complete. Starting FastAPI server on port 8000..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
