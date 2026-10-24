from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()

celery_app = Celery("redteam_worker")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,  # surface errors in dev/tests
    task_routes={
        "app.workers.evaluation_tasks.*": {"queue": "evaluation"},
        "app.workers.redteam_tasks.*": {"queue": "redteam"},
        "app.workers.maintenance_tasks.*": {"queue": "maintenance"},
    },
    task_default_queue="default",
    task_acks_late=True,
    worker_disable_rate_limits=True,
)

celery_app.autodiscover_tasks(["app.workers"])


@celery_setup_logging.connect
def _configure_worker_logging(**_kwargs) -> None:
    # Use the API's structured logging in workers too. Without this, structlog's default
    # console renderer is used, whose tracebacks crash on Windows cp1252 consoles.
    setup_logging()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
