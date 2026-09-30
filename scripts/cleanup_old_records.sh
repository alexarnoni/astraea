#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL não está definida." >&2
  exit 1
fi

echo "[cleanup] Removendo registros com feed_date < hoje - 400 dias..."

# Versoes fixas, iguais as do passo de ML em run_pipeline.sh. Sem fixar, o pip instala
# o SQLAlchemy mais novo, que usa psycopg v3 como driver padrao de postgresql:// e
# falha com "No module named 'psycopg'".
docker run --rm \
  --network astraea_default \
  -e DATABASE_URL="$DATABASE_URL" \
  -v "$PROJECT_ROOT/scripts":/scripts \
  python:3.11-slim bash -c "
    pip install sqlalchemy==2.0.30 psycopg2-binary==2.9.9 -q &&
    python /scripts/cleanup_runner.py
  "

echo "[cleanup] Concluído."
