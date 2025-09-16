#!/bin/bash
set -euo pipefail

# Ensure .env exists
if [ ! -f .env ]; then
  cp .env.example .env
fi

source .env

# Start services
if ! docker compose ps >/dev/null 2>&1; then
  echo "Docker compose not installed or not running?" >&2
  exit 1
fi

docker compose up -d --build

# Wait for Postgres
until docker compose exec db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

# Wait for OpenSearch
until curl -sSf http://localhost:9200 >/dev/null 2>&1; do
  sleep 1
done

# Run migrations
for f in backend/migrations/*.sql; do
  docker compose exec -T db psql -U postgres -d companies < "$f"
done

echo "Backend running at http://localhost:8080" 

echo "Start frontend: (cd frontend && npm install && NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev)"
