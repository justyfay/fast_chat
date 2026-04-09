#!/bin/bash

CELERY_APP="src.fast_chat.tasks.celery_app:celery"

if [[ "${1}" == "celery" ]]; then
    uv run celery --app=${CELERY_APP} worker -l INFO
elif [[ "${1}" == "celery_beat" ]]; then
    uv run celery --app=${CELERY_APP} beat -l DEBUG
elif [[ "${1}" == "flower" ]]; then
    uv run celery --app=${CELERY_APP} flower
fi
