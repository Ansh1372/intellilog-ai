#!/bin/bash
set -e

echo "[ENTRYPOINT] Creating database tables..."
python -m backend.create_tables || echo "Table creation skipped (DB may not be ready yet)"

echo "[ENTRYPOINT] Starting IntelliLog AI..."
exec uvicorn backend.api:app --host 0.0.0.0 --port 8000
