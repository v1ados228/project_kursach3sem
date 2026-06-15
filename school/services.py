"""Сервисный слой: журналирование действий и бизнес-операции."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from school.models import ActionLog, Course, Enrollment

if TYPE_CHECKING:
    pass


def log_action(
    user: User | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
) -> ActionLog:
    """
    Записывает действие пользователя в журнал.

    Args:
        user: Пользователь, выполнивший действие.
        action: Описание действия.
        entity: Тип сущности (Course, Enrollment и т.д.).
        entity_id: ID сущности.

    Returns:
        Созданная запись ActionLog.
    """
    return ActionLog.objects.create(
        user=user,
        action=action,
        entity=entity,
        entity_id=entity_id,
    )


def enroll_user_on_course(user: User, course: Course) -> tuple[Enrollment, bool]:
    """
    Записывает пользователя на курс с проверкой бизнес-правил.

    Args:
        user: Студент.
        course: Курс для записи.

    Returns:
        Кортеж (запись, создана_ли_новая).

    Raises:
        ValidationError: При нарушении бизнес-правил.
    """
    existing = Enrollment.objects.filter(user=user, course=course).first()
    if existing:
        return existing, False
    enrollment = Enrollment(user=user, course=course, status="active")
    enrollment.full_clean()
    enrollment.save()
    log_action(user, "Запись на курс", "Enrollment", enrollment.pk)
    return enrollment, True


def cancel_enrollment(user: User, enrollment: Enrollment) -> Enrollment:
    """
    Отменяет запись студента на курс.

    Args:
        user: Пользователь, инициировавший отмену.
        enrollment: Запись для отмены.

    Raises:
        ValidationError: Если запись уже завершена.
    """
    if enrollment.status == "finished":
        raise ValidationError("Нельзя отменить завершённую запись.")
    enrollment.status = "canceled"
    enrollment.save(update_fields=["status"])
    log_action(user, "Отмена записи", "Enrollment", enrollment.pk)
    return enrollment
