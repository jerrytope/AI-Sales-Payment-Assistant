"""
Celery app configuration for AI Sales Assistant.
"""

import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("ai_sales_assistant")


app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """A debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
