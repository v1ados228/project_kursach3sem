"""Тесты моделей и бизнес-логики."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from school.models import Category, Course, Enrollment, Role
from school.permissions import ROLE_TEACHER, is_teacher, user_has_role
from school.services import enroll_user_on_course, log_action


class RolePermissionTests(TestCase):
    """Тесты проверки ролей."""

    def setUp(self) -> None:
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.user = User.objects.create_user(username="teacher1", password="pass")
        self.teacher_role.users.add(self.user)

    def test_user_has_teacher_role(self) -> None:
        self.assertTrue(user_has_role(self.user, ROLE_TEACHER))

    def test_is_teacher_returns_true(self) -> None:
        self.assertTrue(is_teacher(self.user))


class CourseModelValidationTests(TestCase):
    """Тесты валидации модели Course."""

    def setUp(self) -> None:
        self.category = Category.objects.create(name="Программирование")
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.teacher = User.objects.create_user(username="t1", password="pass")
        self.teacher_role.users.add(self.teacher)
        today = timezone.now().date()

    def test_negative_price_raises_error(self) -> None:
        course = Course(
            category=self.category,
            teacher=self.teacher,
            title="Python",
            description="desc",
            price=Decimal("-100"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        with self.assertRaises(ValidationError):
            course.clean()

    def test_start_after_end_raises_error(self) -> None:
        today = timezone.now().date()
        course = Course(
            category=self.category,
            teacher=self.teacher,
            title="Django",
            description="desc",
            price=Decimal("1000"),
            start_date=today + timedelta(days=10),
            end_date=today,
        )
        with self.assertRaises(ValidationError):
            course.clean()


class EnrollmentValidationTests(TestCase):
    """Тесты валидации записи на курс."""

    def setUp(self) -> None:
        self.category = Category.objects.create(name="Тест")
        self.teacher_role = Role.objects.create(name=ROLE_TEACHER)
        self.teacher = User.objects.create_user(username="t2", password="pass")
        self.teacher_role.users.add(self.teacher)
        self.student = User.objects.create_user(username="s1", password="pass")
        today = timezone.now().date()
        self.course = Course.objects.create(
            category=self.category,
            teacher=self.teacher,
            title="Курс",
            description="desc",
            price=Decimal("3000"),
            start_date=today,
            end_date=today + timedelta(days=30),
            is_published=True,
        )

    def test_cannot_enroll_on_unpublished_course(self) -> None:
        self.course.is_published = False
        self.course.save()
        enrollment = Enrollment(user=self.student, course=self.course)
        with self.assertRaises(ValidationError):
            enrollment.clean()

    def test_enroll_user_on_course_creates_record(self) -> None:
        enrollment, created = enroll_user_on_course(self.student, self.course)
        self.assertTrue(created)
        self.assertEqual(enrollment.status, "active")

    def test_duplicate_enrollment_returns_existing(self) -> None:
        enroll_user_on_course(self.student, self.course)
        enrollment, created = enroll_user_on_course(self.student, self.course)
        self.assertFalse(created)


class ActionLogTests(TestCase):
    """Тесты журнала действий."""

    def test_log_action_creates_record(self) -> None:
        user = User.objects.create_user(username="u1", password="pass")
        log = log_action(user, "Тест", "Course", 1)
        self.assertEqual(log.action, "Тест")
        self.assertEqual(log.entity, "Course")
