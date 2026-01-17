from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Role,
    Category,
    Course,
    Enrollment,
    ActionLog,
)


#INLINE

class CourseInline(admin.TabularInline):
    model = Course
    extra = 0


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    raw_id_fields = ("user",)


class CourseResource(resources.ModelResource):
    class Meta:
        model = Course

    def dehydrate_start_date(self, obj):
        return obj.start_date.strftime("%d-%m-%Y")

    def dehydrate_end_date(self, obj):
        return obj.end_date.strftime("%d-%m-%Y")

    def dehydrate_teacher(self, obj):
        if not obj.teacher:
            return "—"
        full_name = f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return full_name or obj.teacher.username

    def get_category_title(self, obj):
        return obj.category.name

    def dehydrate_category(self, obj):
        return self.get_category_title(obj)


@admin.register(Course)
class CourseAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = CourseResource
    list_display = (
        "title",
        "category",
        "teacher",
        "level",
        "price",
        "start_date",
        "end_date",
        "is_published",
        "enrollment_count",
    )
    list_display_links = ("title",)
    list_filter = ("category", "teacher", "level", "is_published")
    search_fields = ("title", "description")
    date_hierarchy = "start_date"
    inlines = [EnrollmentInline]
    raw_id_fields = ("teacher",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Основное", {"fields": ("title", "description", "category", "teacher", "image")}),
        ("Параметры", {"fields": ("level", "price", "is_published")}),
        ("Даты", {"fields": ("start_date", "end_date")}),
        ("Системные", {"fields": ("created_at", "updated_at")}),
    )

    def get_export_queryset(self, request):
        queryset = super().get_export_queryset(request)
        return queryset.filter(price__gte=5000)

    @admin.display(description="Кол-во записей")
    def enrollment_count(self, obj):
        return obj.enrollment_set.count()


#CATEGORY

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "course_count")
    list_display_links = ("name",)
    list_filter = ("name",)
    search_fields = ("name",)
    inlines = [CourseInline]

    @admin.display(description="Кол-во курсов")
    def course_count(self, obj):
        return obj.course_set.count()


#ENROLLMENT

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "course_category", "status", "enrolled_at")
    list_display_links = ("user", "course")
    list_filter = ("status", "course__category")
    search_fields = ("user__username", "course__title")
    date_hierarchy = "enrolled_at"
    raw_id_fields = ("user", "course")
    readonly_fields = ("enrolled_at",)

    @admin.display(description="Категория")
    def course_category(self, obj):
        return obj.course.category


#ROLE

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "user_count")
    list_display_links = ("name",)
    list_filter = ("name",)
    search_fields = ("name", "users__username")
    filter_horizontal = ("users",)

    @admin.display(description="Пользователей")
    def user_count(self, obj):
        return obj.users.count()


#ACTION LOG

@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ("user", "short_action", "entity", "entity_id", "action_time")
    list_display_links = ("action_time",)
    list_filter = ("entity", "action")
    search_fields = ("user__username", "action", "entity")
    date_hierarchy = "action_time"
    raw_id_fields = ("user",)
    readonly_fields = ("action_time",)

    def short_action(self, obj):
        if len(obj.action) <= 30:
            return obj.action
        return f"{obj.action[:27]}..."

    short_action.short_description = "Действие"

