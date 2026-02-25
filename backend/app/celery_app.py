from celery import Celery

from app.config import settings

celery_app = Celery(
    "pipecanary",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "run-scheduled-checks": {
            "task": "app.tasks.monitoring.run_scheduled_checks",
            "schedule": 3600.0,  # Every hour
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
