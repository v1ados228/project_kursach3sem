from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .filters import CourseFilter, EnrollmentFilter
from .models import Course, Enrollment
from .serializers import CourseSerializer, EnrollmentSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related("category", "teacher")
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "start_date", "price"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        price = self.request.query_params.get("price")
        if price:
            queryset = queryset.filter(price=price)
        if self.request.query_params.get("mine") == "1":
            queryset = queryset.filter(teacher=self.request.user)
        return queryset

    @action(methods=["get"], detail=False, url_path=r"category/(?P<category_id>[^/.]+)")
    def by_category(self, request, category_id):
        queryset = self.get_queryset().filter(category_id=category_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def upcoming(self, request):
        today = timezone.now().date()
        week_end = today + timedelta(days=7)
        queryset = self.get_queryset().filter(start_date__range=(today, week_end))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False)
    def premium_or_tomorrow(self, request):
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
    def foreign_active(self, request):
        queryset = self.get_queryset().filter(
            ~Q(teacher=request.user) & Q(is_published=True)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def enroll(self, request, pk=None):
        course = self.get_object()
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={"status": "active"},
        )
        serializer = EnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(methods=["get"], detail=True)
    def history(self, request, pk=None):
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
    queryset = Enrollment.objects.select_related("user", "course")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = EnrollmentFilter
    ordering_fields = ["enrolled_at"]
    ordering = ["-enrolled_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("mine") == "1":
            queryset = queryset.filter(user=self.request.user)
        return queryset


