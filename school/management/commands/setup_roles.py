"""Создание ролей по умолчанию."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from school.models import Role
from school.permissions import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER


class Command(BaseCommand):
    """Management-команда для инициализации ролей в системе."""

    help = "Создаёт роли Администратор, Преподаватель, Студент."

    def handle(self, *args, **options) -> None:
        for role_name in (ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT):
            _, created = Role.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Создана роль: {role_name}"))
            else:
                self.stdout.write(f"Роль уже существует: {role_name}")
