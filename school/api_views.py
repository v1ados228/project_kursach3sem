"""REST API: курсы и записи на курсы."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from school.filters import CourseFilter, EnrollmentFilter
from school.models import Course, Enrollment
from school.permissions import can_manage_course, is_admin, is_teacher
from school.serializers import CourseSerializer, EnrollmentSerializer
from school.services import enroll_user_on_course, log_action


class StaffWritePermission(BasePermission):
    """Чтение и запись на курс — аутентифицированные; остальная запись — staff."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, "action", None) == "enroll":
            return True
        return request.user.is_staff


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet курсов с аннотациями и кастомными действиями."""

    serializer_class = CourseSerializer
    permission_classes = [StaffWritePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "start_date", "price", "enrollment_count"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[Course]:
        """
        Queryset курсов с select_related и аннотацией enrollment_count.

        Returns:
            Оптимизированный queryset курсов.
        """
        queryset = (
            Course.objects.select_related("category", "teacher")
            .annotate(enrollment_count=Count("enrollment"))
        )
        if not is_admin(self.request.user) and not is_teacher(self.request.user):
            queryset = queryset.filter(is_published=True)
        if self.request.query_params.get("mine") == "1":
            queryset = queryset.filter(teacher=self.request.user)
        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        """
        Передаёт request и список записанных курсов в контекст сериализатора.

        Returns:
            Контекст для CourseSerializer.
        """
        context = super().get_serializer_context()
        request = self.request
        if request.user.is_authenticated:
            context["enrolled_course_ids"] = set(
                Enrollment.objects.filter(user=request.user).values_list(
                    "course_id", flat=True
                )
            )
        return context

    def perform_create(self, serializer: CourseSerializer) -> None:
        """Создаёт курс и записывает действие в журнал."""
        course = serializer.save()
        log_action(self.request.user, "Создание курса", "Course", course.pk)

    def perform_update(self, serializer: CourseSerializer) -> None:
        """Обновляет курс с проверкой прав."""
        course = self.get_object()
        if not can_manage_course(self.request.user, course) and not is_admin(
            self.request.user
        ):
            raise PermissionDenied("Недостаточно прав для редактирования курса.")
        course = serializer.save()
        log_action(self.request.user, "Обновление курса", "Course", course.pk)

    @action(methods=["get"], detail=False, url_path=r"category/(?P<category_id>[^/.]+)")
    def by_category(self, request: Request, category_id: str) -> Response:
        """Курсы выбранной категории."""
        queryset = self.get_queryset().filter(category_id=category_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def upcoming(self, request: Request) -> Response:
        """Курсы, стартующие в ближайшие 7 дней."""
        today = timezone.now().date()
        week_end = today + timedelta(days=7)
        queryset = self.get_queryset().filter(start_date__range=(today, week_end)).order_by(
            "start_date"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def premium_or_tomorrow(self, request: Request) -> Response:
        """Премиум-курсы (цена ≥ 5000) или стартующие завтра."""
        tomorrow = timezone.now().date() + timedelta(days=1)
        queryset = self.get_queryset().filter(
            (Q(price__gte=5000) & Q(is_published=True)) | Q(start_date=tomorrow)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def foreign_active(self, request: Request) -> Response:
        """Опубликованные курсы других преподавателей."""
        queryset = self.get_queryset().filter(
            ~Q(teacher=request.user) & Q(is_published=True)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def complex_catalog(self, request: Request) -> Response:
        """Сложный каталог: продвинутые или python/django курсы."""
        queryset = self.get_queryset().filter(
            (
                Q(level="advanced")
                | Q(title__icontains="python")
                | Q(title__icontains="django")
            )
            & Q(is_published=True)
            & ~Q(teacher=request.user)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def affordable_soon(self, request: Request) -> Response:
        """Доступные курсы: цена ≤ 5000 или старт в ближайшую неделю."""
        week_end = timezone.now().date() + timedelta(days=7)
        queryset = self.get_queryset().filter(
            (Q(price__lte=5000) | Q(start_date__lte=week_end))
            & Q(is_published=True)
            & ~Q(level="advanced")
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def enroll(self, request: Request, pk: int | None = None) -> Response:
        """Запись текущего пользователя на курс."""
        course = self.get_object()
        try:
            enrollment, created = enroll_user_on_course(request.user, course)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        serializer = EnrollmentSerializer(enrollment, context={"request": request})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    @action(methods=["get"], detail=True)
    def history(self, request: Request, pk: int | None = None) -> Response:
        """История изменений курса (simple_history)."""
        course = self.get_object()
        history_data = [
            {
                "history_id": item.history_id,
                "history_date": item.history_date,
                "history_type": item.history_type,
                "history_user": getattr(item.history_user, "username", None),
                "title": item.title,
                "price": item.price,
                "start_date": item.start_date,
                "end_date": item.end_date,
            }
            for item in course.history.all()[:50]
        ]
        return Response(history_data)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet записей на курсы."""

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = EnrollmentFilter
    ordering_fields = ["enrolled_at"]
    ordering = ["-enrolled_at"]

    def get_queryset(self) -> QuerySet[Enrollment]:
        """
        Queryset записей с select_related.

        Студенты видят только свои записи; преподаватели — записи на свои курсы.
        """
        queryset = Enrollment.objects.select_related(
            "user", "course", "course__category", "course__teacher"
        )
        user = self.request.user
        if is_admin(user):
            return queryset
        if self.request.query_params.get("mine") == "1":
            return queryset.filter(user=user)
        if is_teacher(user):
            return queryset.filter(
                Q(user=user) | Q(course__teacher=user)
            )
        return queryset.filter(user=user)

    def get_serializer_context(self) -> dict[str, Any]:
        """Передаёт request в контекст сериализатора."""
        return super().get_serializer_context()

    def perform_create(self, serializer: EnrollmentSerializer) -> None:
        """Создаёт запись: студент — только на себя."""
        if self.request.user.is_staff:
            enrollment = serializer.save()
        else:
            enrollment = serializer.save(user=self.request.user, status="active")
        log_action(self.request.user, "Создание записи", "Enrollment", enrollment.pk)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Обновление записи — только для staff."""
        if not request.user.is_staff:
            return Response(
                {"detail": "Недостаточно прав."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Удаление записи — только для staff."""
        if not request.user.is_staff:
            return Response(
                {"detail": "Недостаточно прав."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
