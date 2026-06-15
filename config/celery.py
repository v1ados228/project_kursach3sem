"""Инициализация Celery для проекта."""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-course-start-reminders": {
        "task": "school.send_course_start_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "cleanup-old-action-logs": {
        "task": "school.cleanup_old_action_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
    "finish-expired-enrollments": {
        "task": "school.finish_expired_enrollments",
        "schedule": crontab(hour=1, minute=0),
    },
}
