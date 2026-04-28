#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-api}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/4] Atualizando código do git..."
cd "$PROJECT_ROOT"
git pull

echo "[2/4] Rebuildando serviço: $SERVICE"
docker compose up -d --build "$SERVICE"

echo "[3/4] Aguardando container subir..."
sleep 5

echo "[4/4] Verificando status..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep "astraea-$SERVICE" || true

echo ""
echo "Deploy completo. Verifique logs com:"
echo "  docker logs astraea-$SERVICE-1 --tail 30"
