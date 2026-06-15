"""Проверка ролей и прав доступа пользователей."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User

if TYPE_CHECKING:
    from school.models import Course, Enrollment

ROLE_ADMIN = "Администратор"
ROLE_TEACHER = "Преподаватель"
ROLE_STUDENT = "Студент"


def user_has_role(user: User, role_name: str) -> bool:
    """
    Проверяет, назначена ли пользователю указанная роль.

    Args:
        user: Объект пользователя Django.
        role_name: Название роли (например, «Преподаватель»).

    Returns:
        True, если роль назначена или пользователь — staff (для администратора).
    """
    if not user.is_authenticated:
        return False
    if role_name == ROLE_ADMIN and user.is_staff:
        return True
    return user.roles.filter(name__iexact=role_name).exists()


def is_admin(user: User) -> bool:
    """Пользователь — администратор (staff)."""
    return user.is_authenticated and user.is_staff


def is_teacher(user: User) -> bool:
    """Пользователь — преподаватель или администратор."""
    return is_admin(user) or user_has_role(user, ROLE_TEACHER)


def is_student(user: User) -> bool:
    """Пользователь — студент."""
    return user.is_authenticated and user_has_role(user, ROLE_STUDENT)


def can_manage_course(user: User, course: Course) -> bool:
    """
    Может ли пользователь редактировать курс.

    Args:
        user: Текущий пользователь.
        course: Объект курса.

    Returns:
        True для администратора или преподавателя-владельца курса.
    """
    if is_admin(user):
        return True
    return is_teacher(user) and course.teacher_id == user.id


def can_view_enrollment(user: User, enrollment: Enrollment) -> bool:
    """
    Может ли пользователь просматривать запись на курс.

    Args:
        user: Текущий пользователь.
        enrollment: Объект записи.

    Returns:
        True для администратора, студента-владельца или преподавателя курса.
    """
    if is_admin(user):
        return True
    if enrollment.user_id == user.id:
        return True
    return is_teacher(user) and enrollment.course.teacher_id == user.id
