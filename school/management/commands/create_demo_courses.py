from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from school.models import Category, Course, Enrollment


class Command(BaseCommand):
    help = "Создает тестовые курсы и записи для демонстрации."

    def add_arguments(self, parser):
        parser.add_argument(
            "--teacher",
            default="teacher",
            help="Имя пользователя преподавателя.",
        )
        parser.add_argument(
            "--student",
            default="student",
            help="Имя пользователя студента.",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Количество курсов для создания.",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        teacher, _ = user_model.objects.get_or_create(username=options["teacher"])
        student, _ = user_model.objects.get_or_create(username=options["student"])

        category, _ = Category.objects.get_or_create(name="Программирование")
        today = timezone.now().date()

        created_courses = 0
        created_enrollments = 0

        for index in range(1, options["count"] + 1):
            course, created = Course.objects.get_or_create(
                category=category,
                title=f"Курс {index}",
                defaults={
                    "description": "Демо-курс онлайн-школы.",
                    "teacher": teacher,
                    "price": 3000 + index * 500,
                    "level": "beginner",
                    "start_date": today + timedelta(days=index * 3),
                    "end_date": today + timedelta(days=index * 3 + 30),
                    "is_published": True,
                },
            )
            if created:
                created_courses += 1

            enrollment, created_enrollment = Enrollment.objects.get_or_create(
                user=student,
                course=course,
                defaults={"status": "active"},
            )
            if created_enrollment:
                created_enrollments += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Курсов: {created_courses}, записей: {created_enrollments}"
            )
        )
