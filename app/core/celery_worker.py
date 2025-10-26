# app/core/celery_worker.py

from celery import Celery
from app.core.config import settings

# Initialize the Celery app instance
celery_app = Celery(
    'rag_worker', # Name of the Celery application
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure timezones and other options
# Note: Use the 'app.' prefix when referring to tasks in other modules later
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='America/New_York', # Set to a known timezone for consistency
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    imports=('app.core.tasks',)
)

