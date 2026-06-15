"""Периодические и фоновые задачи Celery."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone

from school.models import ActionLog, Course, Enrollment


@shared_task(name="school.send_course_start_reminders")
def send_course_start_reminders() -> int:
    """
    Отправляет напоминания студентам о курсах, стартующих завтра.

    Returns:
        Количество отправленных писем.
    """
    tomorrow = timezone.now().date() + timedelta(days=1)
    courses = Course.objects.filter(start_date=tomorrow, is_published=True)
    sent = 0
    for course in courses:
        enrollments = Enrollment.objects.filter(
            course=course, status="active"
        ).select_related("user")
        for enrollment in enrollments:
            user = enrollment.user
            if user.email:
                send_mail(
                    subject=f"Напоминание: завтра стартует курс «{course.title}»",
                    message=(
                        f"Здравствуйте, {user.get_full_name() or user.username}!\n\n"
                        f"Напоминаем, что курс «{course.title}» начинается "
                        f"{course.start_date}.\n"
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                sent += 1
    return sent


@shared_task(name="school.cleanup_old_action_logs")
def cleanup_old_action_logs(days: int = 90) -> int:
    """
    Удаляет записи журнала действий старше указанного числа дней.

    Args:
        days: Порог давности в днях.

    Returns:
        Количество удалённых записей.
    """
    threshold = timezone.now() - timedelta(days=days)
    deleted, _ = ActionLog.objects.filter(action_time__lt=threshold).delete()
    return deleted


@shared_task(name="school.finish_expired_enrollments")
def finish_expired_enrollments() -> int:
    """
    Автоматически завершает записи на курсы, дата окончания которых прошла.

    Returns:
        Количество обновлённых записей.
    """
    today = timezone.now().date()
    updated = Enrollment.objects.filter(
        status="active",
        course__end_date__lt=today,
    ).update(status="finished")
    return updated
