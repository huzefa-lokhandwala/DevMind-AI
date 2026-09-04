#!/bin/bash
set -e

echo "[DevMind-AI] Starting application container..."

echo "[DevMind-AI] Running Alembic database migrations..."
alembic upgrade head

PORT="${PORT:-8000}"
echo "[DevMind-AI] Alembic migrations complete. Starting FastAPI server on port ${PORT} (workers=1)..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
