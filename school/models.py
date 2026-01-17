from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Role(models.Model):
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

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("Название категории", max_length=255)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Категория курса"
        verbose_name_plural = "Категории курсов"

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ("beginner", "Начальный"),
        ("intermediate", "Средний"),
        ("advanced", "Продвинутый"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="Категория"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Преподаватель"
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

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('finished', 'Завершён'),
        ('canceled', 'Отменён'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        verbose_name="Курс"
    )
    enrolled_at = models.DateTimeField("Дата записи", auto_now_add=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    class Meta:
        verbose_name = "Запись на курс"
        verbose_name_plural = "Записи на курсы"
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} → {self.course.title}"


class ActionLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь"
    )
    action = models.CharField("Действие", max_length=255)
    entity = models.CharField("Сущность", max_length=100)
    entity_id = models.PositiveIntegerField("ID сущности", null=True, blank=True)
    action_time = models.DateTimeField("Время действия", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал действий"
        verbose_name_plural = "Журнал действий"

    def __str__(self):
        return f"{self.user} — {self.action} ({self.entity} #{self.entity_id})"