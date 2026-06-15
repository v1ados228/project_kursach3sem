"""Тесты форм и веб-представлений."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from school.forms import CategoryForm, CourseForm
from school.models import Category, Course, Role
from school.permissions import ROLE_TEACHER


@override_settings(ENABLE_SILK=False)
class FormValidationTests(TestCase):
    """Тесты валидации форм."""

    def test_category_name_with_digits_invalid(self) -> None:
        form = CategoryForm(data={"name": "Категория123", "description": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_course_negative_price_invalid(self) -> None:
        category = Category.objects.create(name="IT")
        teacher_role = Role.objects.create(name=ROLE_TEACHER)
        teacher = User.objects.create_user(username="t", password="pass")
        teacher_role.users.add(teacher)
        today = timezone.now().date()
        form = CourseForm(
            data={
                "title": "Курс",
                "description": "desc",
                "category": category.pk,
                "teacher": teacher.pk,
                "start_date": today,
                "end_date": today,
                "price": "-100",
                "level": "beginner",
                "is_published": True,
            }
        )
        self.assertFalse(form.is_valid())


@override_settings(ENABLE_SILK=False)
class WebViewTests(TestCase):
    """Тесты веб-страниц."""

    def setUp(self) -> None:
        self.client = Client()
        self.category = Category.objects.create(name="Web")
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.teacher = User.objects.create_user(username="teach", password="pass")
        self.teacher_role.users.add(self.teacher)
        today = timezone.now().date()
        self.course = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="HTML",
            description="desc",
            price=Decimal("2000"),
            start_date=today,
            end_date=today,
            is_published=True,
        )

    def test_course_list_page_loads(self) -> None:
        response = self.client.get(reverse("school:course_list"))
        self.assertEqual(response.status_code, 200)

    def test_category_list_page_loads(self) -> None:
        response = self.client.get(reverse("school:category_list"))
        self.assertEqual(response.status_code, 200)
