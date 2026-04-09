from celery import Celery

from config import settings

celery: Celery = Celery(
    name="tasks",
    broker=settings.redis_url,
    result_backend=settings.redis_url,
    include=["src.fast_chat.tasks.tasks"],
)
celery.conf.enable_utc = True
celery.conf.timezone = "UTC"
