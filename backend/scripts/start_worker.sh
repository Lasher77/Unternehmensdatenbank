#!/bin/sh
set -euo pipefail

python scripts/run_migrations.py
exec celery -A app.workers.celery_app worker -l info
