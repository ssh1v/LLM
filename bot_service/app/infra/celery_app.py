from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "bot_service",
    broker=settings.rabbitmq_url,   # RabbitMQ — брокер задач
    backend=settings.redis_url,     # Redis — result backend
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Регистрация задач (импорт модуля, а не конкретного объекта — чтобы
# избежать проблем с циклическим импортом).
celery_app.autodiscover_tasks(["app.tasks"])
from app.tasks import llm_tasks  # noqa: E402,F401
