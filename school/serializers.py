"""DRF-сериализаторы для API онлайн-школы."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers

from school.models import Course, Enrollment


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса с вычисляемыми полями через SerializerMethodField."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    teacher_username = serializers.CharField(source="teacher.username", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    teacher_full_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "teacher",
            "teacher_username",
            "teacher_full_name",
            "image",
            "price",
            "level",
            "level_display",
            "start_date",
            "end_date",
            "duration_days",
            "is_published",
            "enrollment_count",
            "is_enrolled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_enrollment_count(self, obj: Course) -> int:
        """
        Количество записей на курс.

        Args:
            obj: Объект курса (может содержать аннотацию enrollment_count).

        Returns:
            Число активных записей.
        """
        if hasattr(obj, "enrollment_count"):
            return obj.enrollment_count
        return obj.enrollment_set.count()

    def get_duration_days(self, obj: Course) -> int:
        """
        Длительность курса в днях.

        Args:
            obj: Объект курса.

        Returns:
            Разница между датой окончания и старта в днях.
        """
        return (obj.end_date - obj.start_date).days

    def get_is_enrolled(self, obj: Course) -> bool:
        """
        Записан ли текущий пользователь на курс.

        Использует контекст сериализатора (ключ ``request``).

        Args:
            obj: Объект курса.

        Returns:
            True, если аутентифицированный пользователь записан на курс.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        enrolled_ids: set[int] | None = self.context.get("enrolled_course_ids")
        if enrolled_ids is not None:
            return obj.pk in enrolled_ids
        return obj.enrollment_set.filter(user=request.user).exists()

    def get_teacher_full_name(self, obj: Course) -> str | None:
        """
        Полное имя преподавателя.

        Args:
            obj: Объект курса.

        Returns:
            ФИО или username преподавателя.
        """
        if not obj.teacher:
            return None
        full_name = obj.teacher.get_full_name().strip()
        return full_name or obj.teacher.username

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Валидация дат курса.

        Args:
            attrs: Поля для сохранения.

        Returns:
            Проверенные атрибуты.

        Raises:
            ValidationError: Если дата старта позже даты окончания.
        """
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Дата старта не может быть позже даты окончания."
            )
        return attrs

    def validate_price(self, value: Any) -> Any:
        """
        Валидация цены курса.

        Args:
            value: Значение цены.

        Returns:
            Проверенная цена.

        Raises:
            ValidationError: Если цена не положительна.
        """
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной.")
        return value

    def validate_title(self, value: str) -> str:
        """
        Уникальность названия курса в категории.

        Args:
            value: Название курса.

        Returns:
            Проверенное название.

        Raises:
            ValidationError: При дублировании названия в категории.
        """
        category_id = self.initial_data.get("category")
        if not category_id and self.instance:
            category_id = getattr(self.instance, "category_id", None)
        if category_id:
            queryset = Course.objects.filter(category_id=category_id, title=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "Название курса должно быть уникальным в категории."
                )
        return value


class EnrollmentSerializer(serializers.ModelSerializer):
    """Сериализатор записи на курс."""

    user_username = serializers.CharField(source="user.username", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_price = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "user",
            "user_username",
            "course",
            "course_title",
            "course_price",
            "status",
            "enrolled_at",
            "can_cancel",
        ]
        read_only_fields = ["enrolled_at"]

    def get_course_price(self, obj: Enrollment) -> str:
        """
        Цена курса записи.

        Args:
            obj: Объект записи.

        Returns:
            Строковое представление цены.
        """
        return str(obj.course.price)

    def get_can_cancel(self, obj: Enrollment) -> bool:
        """
        Может ли текущий пользователь отменить запись.

        Использует контекст сериализатора (ключ ``request``).

        Args:
            obj: Объект записи.

        Returns:
            True, если отмена разрешена.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.status != "active":
            return False
        return request.user.is_staff or obj.user_id == request.user.id

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Валидация записи на курс по бизнес-правилам.

        Args:
            attrs: Поля для сохранения.

        Returns:
            Проверенные атрибуты.

        Raises:
            ValidationError: При нарушении бизнес-правил.
        """
        user = attrs.get("user") or getattr(self.instance, "user", None)
        course = attrs.get("course") or getattr(self.instance, "course", None)
        if user and course:
            if not course.is_published:
                raise serializers.ValidationError(
                    {"course": "Нельзя записаться на неопубликованный курс."}
                )
            queryset = Enrollment.objects.filter(user=user, course=course)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"course": "Вы уже записаны на этот курс."}
                )
        return attrs
