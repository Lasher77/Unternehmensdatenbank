#!/bin/sh
set -euo pipefail

python scripts/run_migrations.py
CONCURRENCY="${CELERY_CONCURRENCY:-4}"
exec celery -A app.workers.celery_app worker -l info --concurrency="${CONCURRENCY}"
