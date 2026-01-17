import django_filters

from .models import Course, Enrollment


class CourseFilter(django_filters.FilterSet):
    start_date_range = django_filters.DateFromToRangeFilter(field_name="start_date")
    end_date_range = django_filters.DateFromToRangeFilter(field_name="end_date")

    class Meta:
        model = Course
        fields = ["category", "teacher", "level", "is_published", "start_date", "end_date"]


class EnrollmentFilter(django_filters.FilterSet):
    enrolled_range = django_filters.DateFromToRangeFilter(field_name="enrolled_at")

    class Meta:
        model = Enrollment
        fields = ["status", "course", "user", "enrolled_range"]
