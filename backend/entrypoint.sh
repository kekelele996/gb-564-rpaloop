#!/bin/sh
set -e

echo "[entrypoint] $(date -Iseconds) alembic upgrade head"
alembic upgrade head

if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "[entrypoint] $(date -Iseconds) seed demo data"
  python -m scripts.seed_demo || echo "[entrypoint] seed failed (non blocking)"
fi

echo "[entrypoint] $(date -Iseconds) starting uvicorn on :8000"
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
