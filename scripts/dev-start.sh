#!/bin/bash
set -euo pipefail

# Ensure .env exists
if [ ! -f .env ]; then
  cp .env.example .env
fi

# Start services
if ! docker compose ps >/dev/null 2>&1; then
  echo "Docker compose not installed or not running?" >&2
  exit 1
fi

docker compose up -d --build

# Run migrations
for f in backend/migrations/*.sql; do
  docker compose exec -T db psql -U postgres -d companies < "$f"
done

echo "Backend running at http://localhost:8080" 

echo "Start frontend: (cd frontend && npm install && NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev)"
