#!/usr/bin/env bash
# run_pipeline.sh — Executa o pipeline completo: dbt run → ML scoring
# Uso: bash scripts/run_pipeline.sh
# Requer: DATABASE_URL definida como variável de ambiente do sistema

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Validação ──────────────────────────────────────────────────────────────────
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL não está definida." >&2
  exit 1
fi

echo "[1/2] Rodando dbt (stg_asteroids+)..."
cd "$PROJECT_ROOT/dbt/astraea"
dbt run --select stg_asteroids+
echo "[1/2] dbt concluído."

echo "[2/2] Rodando ML scoring (predict.py)..."
docker run --rm \
  -v "$PROJECT_ROOT":/app \
  -w /app \
  -e DATABASE_URL="$DATABASE_URL" \
  python:3.11-slim \
  bash -c "pip install -q -r ml/requirements.txt && python ml/predict.py"
echo "[2/2] ML scoring concluído."

echo "Pipeline finalizado com sucesso."
