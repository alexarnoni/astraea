#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL não está definida." >&2
  exit 1
fi

echo "[cleanup] Removendo registros com feed_date < hoje - 30 dias..."

docker run --rm \
  --network astraea_default \
  -e DATABASE_URL="$DATABASE_URL" \
  -v "$PROJECT_ROOT/scripts":/scripts \
  python:3.11-slim bash -c "
    pip install psycopg2-binary sqlalchemy -q &&
    python /scripts/cleanup_runner.py
  "

echo "[cleanup] Concluído."
