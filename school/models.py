from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

if TYPE_CHECKING:
    pass


class Role(models.Model):
    """Роль пользователя в системе (Администратор, Преподаватель, Студент)."""

    name = models.CharField("Название роли", max_length=50)
    users = models.ManyToManyField(
        User,
        verbose_name="Пользователи",
        related_name="roles",
        blank=True,
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Категория курсов (например, «Программирование»)."""

    name = models.CharField("Название категории", max_length=255)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Категория курса"
        verbose_name_plural = "Категории курсов"

    def __str__(self) -> str:
        return self.name


class Course(models.Model):
    """Курс онлайн-школы с преподавателем, ценой и датами проведения."""

    LEVEL_CHOICES = [
        ("beginner", "Начальный"),
        ("intermediate", "Средний"),
        ("advanced", "Продвинутый"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="Категория",
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Преподаватель",
    )
    title = models.CharField("Название курса", max_length=255)
    description = models.TextField("Описание")
    image = models.ImageField(
        "Обложка курса",
        upload_to="courses/",
        blank=True,
        null=True,
    )
    price = models.DecimalField("Цена", max_digits=8, decimal_places=2)
    level = models.CharField(
        "Уровень",
        max_length=20,
        choices=LEVEL_CHOICES,
        default="beginner",
    )
    start_date = models.DateField("Дата старта", default=timezone.now)
    end_date = models.DateField("Дата окончания", default=timezone.now)
    is_published = models.BooleanField("Опубликован", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "title"],
                name="unique_course_title_per_category",
            )
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        """
        Валидация бизнес-правил курса.

        Raises:
            ValidationError: При нарушении правил цены или дат.
        """
        super().clean()
        if self.price is not None and self.price <= Decimal("0"):
            raise ValidationError({"price": "Цена должна быть положительной."})
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                {"end_date": "Дата старта не может быть позже даты окончания."}
            )
        if self.teacher_id and not self.teacher.roles.filter(
            name__iexact="Преподаватель"
        ).exists():
            raise ValidationError(
                {"teacher": "Преподаватель должен иметь роль «Преподаватель»."}
            )


class Enrollment(models.Model):
    """Запись пользователя на курс."""

    STATUS_CHOICES = [
        ("active", "Активен"),
        ("finished", "Завершён"),
        ("canceled", "Отменён"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        verbose_name="Курс",
    )
    enrolled_at = models.DateTimeField("Дата записи", auto_now_add=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    class Meta:
        verbose_name = "Запись на курс"
        verbose_name_plural = "Записи на курсы"
        unique_together = ("user", "course")

    def __str__(self) -> str:
        return f"{self.user.username} → {self.course.title}"

    def clean(self) -> None:
        """
        Валидация бизнес-правил записи на курс.

        Raises:
            ValidationError: При записи на неопубликованный или завершённый курс.
        """
        super().clean()
        if not self.course_id:
            return
        course = self.course
        if not course.is_published:
            raise ValidationError(
                {"course": "Нельзя записаться на неопубликованный курс."}
            )
        today = timezone.now().date()
        if course.end_date < today:
            raise ValidationError(
                {"course": "Нельзя записаться на курс, который уже завершился."}
            )
        if self.pk is None and self.status == "active" and self.user_id:
            if Enrollment.objects.filter(
                user_id=self.user_id,
                course_id=self.course_id,
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    {"course": "Вы уже записаны на этот курс."}
                )


class ActionLog(models.Model):
    """Журнал действий пользователей в системе."""

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь",
    )
    action = models.CharField("Действие", max_length=255)
    entity = models.CharField("Сущность", max_length=100)
    entity_id = models.PositiveIntegerField("ID сущности", null=True, blank=True)
    action_time = models.DateTimeField("Время действия", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал действий"
        verbose_name_plural = "Журнал действий"

    def __str__(self) -> str:
        return f"{self.user} — {self.action} ({self.entity} #{self.entity_id})"
