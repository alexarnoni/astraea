#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL não está definida." >&2
  exit 1
fi

echo "[cleanup] Removendo registros com close_approach_date < hoje - 30 dias..."

docker run --rm \
  --network astraea_default \
  -e DATABASE_URL="$DATABASE_URL" \
  python:3.11-slim bash -c "
    pip install psycopg2-binary sqlalchemy -q &&
    python -c \"
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text(\\\"
        DELETE FROM raw.neo_feeds
        WHERE feed_date < CURRENT_DATE - INTERVAL '30 days'
    \\\"))
    conn.commit()
    print(f'[cleanup] Removidos {result.rowcount} registros de raw.neo_feeds')
\"
  "

echo "[cleanup] Concluído."
