#!/bin/bash

uv run alembic upgrade head
# TO-DO: Вернуть 4 воркера после настройки на Redis pub/sub между воркерами
uv run gunicorn fast_chat.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000
