#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL não está definida." >&2
  exit 1
fi

echo "[1/2] Rodando dbt..."
docker run --rm \
  --network astraea_default \
  -v "$PROJECT_ROOT/dbt":/dbt \
  -w /dbt/astraea \
  python:3.11-slim bash -c "
    pip install dbt-postgres==1.8.2 -q &&
    dbt run --profiles-dir /dbt/profiles
  "
echo "[1/2] dbt concluído."

echo "[2/2] Rodando ML scoring..."
docker run --rm \
  --network astraea_default \
  -v "$PROJECT_ROOT/ml":/ml \
  -e DATABASE_URL="$DATABASE_URL" \
  -w /ml \
  python:3.11-slim bash -c "
    pip install scikit-learn==1.5.2 pandas==2.2.2 sqlalchemy==2.0.30 \
      psycopg2-binary==2.9.9 joblib==1.4.2 numpy==1.26.4 \
      python-dotenv==1.0.1 pg8000==1.31.2 -q &&
    python predict.py
  "
echo "[2/2] ML scoring concluído."

echo "Pipeline finalizado com sucesso."
