#!/bin/bash
set -euxo pipefail

# Let the DB and Redis start
python /code/app/prestart.py

# Run migrations
alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 80 --log-config /code/app/log_config.json
