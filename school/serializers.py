from rest_framework import serializers

from .models import Course, Enrollment


class CourseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    teacher_username = serializers.CharField(source="teacher.username", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)

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
            "image",
            "price",
            "level",
            "level_display",
            "start_date",
            "end_date",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Дата старта не может быть позже даты окончания."
            )
        return attrs

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной.")
        return value

    def validate_title(self, value):
        category_id = self.initial_data.get("category")
        if not category_id and self.instance:
            category_id = getattr(self.instance, "category_id", None)
        if category_id:
            queryset = Course.objects.filter(category_id=category_id, title=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Название курса должно быть уникальным в категории.")
        return value


class EnrollmentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "user",
            "user_username",
            "course",
            "course_title",
            "status",
            "enrolled_at",
        ]
        read_only_fields = ["enrolled_at"]


