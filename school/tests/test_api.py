"""Тесты REST API."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from school.models import Category, Course, Enrollment, Role
from school.permissions import ROLE_TEACHER


@override_settings(ENABLE_SILK=False)
class CourseAPITests(TestCase):
    """Тесты API курсов."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.category = Category.objects.create(name="IT")
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.teacher_role.users.add(self.teacher)
        self.student = User.objects.create_user(username="student", password="pass")
        today = timezone.now().date()
        self.course = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="Python Basics",
            description="desc",
            price=Decimal("4500"),
            start_date=today + timedelta(days=3),
            end_date=today + timedelta(days=33),
            is_published=True,
        )
        self.client.force_authenticate(user=self.student)

    def test_list_courses_returns_published(self) -> None:
        response = self.client.get("/api/courses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_price_min(self) -> None:
        response = self.client.get("/api/courses/", {"price_min": "4000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_category(self) -> None:
        response = self.client.get("/api/courses/", {"category": self.category.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_serializer_has_enrollment_count_annotation(self) -> None:
        response = self.client.get(f"/api/courses/{self.course.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("enrollment_count", response.data)
        self.assertIn("is_enrolled", response.data)
        self.assertIn("duration_days", response.data)

    def test_enroll_on_course(self) -> None:
        response = self.client.post(f"/api/courses/{self.course.pk}/enroll/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(user=self.student, course=self.course).exists()
        )

    def test_upcoming_courses_endpoint(self) -> None:
        response = self.client.get("/api/courses/upcoming/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(ENABLE_SILK=False)
class EnrollmentAPITests(TestCase):
    """Тесты API записей."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.category = Category.objects.create(name="IT")
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.teacher = User.objects.create_user(username="t", password="pass")
        self.teacher_role.users.add(self.teacher)
        self.student = User.objects.create_user(username="s", password="pass")
        today = timezone.now().date()
        self.course = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="Django",
            description="desc",
            price=Decimal("5000"),
            start_date=today,
            end_date=today + timedelta(days=30),
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student, course=self.course, status="active"
        )
        self.client.force_authenticate(user=self.student)

    def test_student_sees_only_own_enrollments(self) -> None:
        other = User.objects.create_user(username="other", password="pass")
        Enrollment.objects.create(user=other, course=self.course, status="active")
        response = self.client.get("/api/enrollments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_enrollment_has_can_cancel_field(self) -> None:
        response = self.client.get(f"/api/enrollments/{self.enrollment.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["can_cancel"])
