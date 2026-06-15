"""Фильтрация курсов и записей через django-filter."""

from __future__ import annotations

import django_filters

from school.models import Course, Enrollment


class CourseFilter(django_filters.FilterSet):
    """
    Фильтр курсов по цене, категории, преподавателю и другим критериям.

    Аналог фильтрации товаров: цена → price, категория → category,
    производитель → teacher (преподаватель).
    """

    start_date_range = django_filters.DateFromToRangeFilter(field_name="start_date")
    end_date_range = django_filters.DateFromToRangeFilter(field_name="end_date")
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    price = django_filters.NumberFilter(field_name="price")

    class Meta:
        model = Course
        fields = [
            "category",
            "teacher",
            "level",
            "is_published",
            "start_date",
            "end_date",
            "price",
            "price_min",
            "price_max",
        ]


class EnrollmentFilter(django_filters.FilterSet):
    """Фильтр записей на курсы."""

    enrolled_range = django_filters.DateFromToRangeFilter(field_name="enrolled_at")

    class Meta:
        model = Enrollment
        fields = ["status", "course", "user", "enrolled_range"]
