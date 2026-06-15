"""Веб-представления (CBV) онлайн-школы."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Avg, Count, QuerySet
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from school.forms import (
    CategoryForm,
    CourseForm,
    EnrollmentCreateForm,
    EnrollmentForm,
    SignUpForm,
)
from school.models import Category, Course, Enrollment
from school.permissions import can_manage_course, is_admin, is_teacher
from school.services import cancel_enrollment, log_action


class StaffRequiredMixin(UserPassesTestMixin):
    """Доступ только для администраторов (is_staff)."""

    def test_func(self) -> bool:
        return self.request.user.is_staff


class TeacherOrStaffMixin(UserPassesTestMixin):
    """Доступ для преподавателей и администраторов."""

    def test_func(self) -> bool:
        return is_teacher(self.request.user)


class CategoryListView(ListView):
    """Список категорий с аннотацией количества курсов."""

    model = Category
    template_name = "school/category_list.html"
    context_object_name = "categories"
    paginate_by = 9

    def get_queryset(self) -> QuerySet[Category]:
        return Category.objects.annotate(
            course_count=Count("course"),
            avg_price=Avg("course__price"),
        ).order_by("name")


class CategoryDetailView(DetailView):
    """Детальная страница категории с курсами."""

    model = Category
    template_name = "school/category_detail.html"
    context_object_name = "category"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = (
            self.object.course_set.select_related("teacher")
            .annotate(enrollment_count=Count("enrollment"))
            .order_by("-created_at")
        )
        if not is_admin(self.request.user) and not is_teacher(self.request.user):
            courses = courses.filter(is_published=True)
        context["courses"] = courses
        return context


class CategoryCreateView(StaffRequiredMixin, CreateView):
    """Создание категории (только администратор)."""

    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"
    success_url = reverse_lazy("school:category_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, "Создание категории", "Category", self.object.pk)
        return response


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    """Редактирование категории."""

    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"

    def get_success_url(self):
        return reverse_lazy("school:category_detail", kwargs={"pk": self.object.pk})


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    """Удаление категории."""

    model = Category
    context_object_name = "category"
    template_name = "school/category_confirm_delete.html"
    success_url = reverse_lazy("school:category_list")


class CourseDetailView(DetailView):
    """Детальная страница курса."""

    model = Course
    template_name = "school/course_detail.html"
    context_object_name = "course"

    def get_queryset(self) -> QuerySet[Course]:
        return Course.objects.select_related("category", "teacher").annotate(
            enrollment_count=Count("enrollment")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if is_admin(self.request.user) or self.object.teacher_id == self.request.user.id:
            context["enrollments"] = (
                self.object.enrollment_set.select_related("user").order_by("-enrolled_at")
            )
        else:
            context["enrollments"] = None
        if self.request.user.is_authenticated:
            enrollment = self.object.enrollment_set.filter(user=self.request.user).first()
            context["user_enrollment"] = enrollment
            context["is_enrolled"] = enrollment is not None
        else:
            context["is_enrolled"] = False
            context["user_enrollment"] = None
        return context


class CourseListView(ListView):
    """Список курсов с фильтрацией и select_related."""

    model = Course
    template_name = "school/course_list.html"
    context_object_name = "courses"
    paginate_by = 6

    def get_queryset(self) -> QuerySet[Course]:
        queryset = (
            Course.objects.select_related("category", "teacher")
            .annotate(enrollment_count=Count("enrollment"))
            .order_by("-created_at")
        )
        if not is_admin(self.request.user) and not is_teacher(self.request.user):
            queryset = queryset.filter(is_published=True)
        category_id = self.request.GET.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.order_by("name")
        context["selected_category"] = self.request.GET.get("category", "")
        return context


class CourseCreateView(TeacherOrStaffMixin, CreateView):
    """Создание курса (преподаватель или администратор)."""

    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"
    success_url = reverse_lazy("school:course_list")

    def form_valid(self, form):
        if is_teacher(self.request.user) and not is_admin(self.request.user):
            form.instance.teacher = self.request.user
        response = super().form_valid(form)
        log_action(self.request.user, "Создание курса", "Course", self.object.pk)
        return response


class CourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование курса (владелец или администратор)."""

    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"

    def test_func(self) -> bool:
        course = self.get_object()
        return can_manage_course(self.request.user, course)

    def get_success_url(self):
        return reverse_lazy("school:course_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request.user, "Обновление курса", "Course", self.object.pk)
        return response


class CourseDeleteView(StaffRequiredMixin, DeleteView):
    """Удаление курса (только администратор)."""

    model = Course
    context_object_name = "course"
    template_name = "school/course_confirm_delete.html"
    success_url = reverse_lazy("school:course_list")


class EnrollmentListView(LoginRequiredMixin, ListView):
    """Список записей на курсы."""

    model = Enrollment
    template_name = "school/enrollment_list.html"
    context_object_name = "enrollments"
    paginate_by = 10

    def get_queryset(self) -> QuerySet[Enrollment]:
        queryset = Enrollment.objects.select_related(
            "user", "course", "course__category", "course__teacher"
        )
        if is_admin(self.request.user):
            return queryset.order_by("-enrolled_at")
        if is_teacher(self.request.user):
            return queryset.filter(
                models.Q(user=self.request.user)
                | models.Q(course__teacher=self.request.user)
            ).order_by("-enrolled_at")
        return queryset.filter(user=self.request.user).order_by("-enrolled_at")


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница записи."""

    model = Enrollment
    template_name = "school/enrollment_detail.html"
    context_object_name = "enrollment"

    def get_queryset(self) -> QuerySet[Enrollment]:
        queryset = Enrollment.objects.select_related(
            "user", "course", "course__category", "course__teacher"
        )
        if is_admin(self.request.user):
            return queryset
        if is_teacher(self.request.user):
            return queryset.filter(
                models.Q(user=self.request.user)
                | models.Q(course__teacher=self.request.user)
            )
        return queryset.filter(user=self.request.user)


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """Запись студента на курс."""

    model = Enrollment
    form_class = EnrollmentCreateForm
    template_name = "school/enrollment_form.html"
    success_url = reverse_lazy("school:enrollment_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = "active"
        response = super().form_valid(form)
        log_action(self.request.user, "Запись на курс", "Enrollment", self.object.pk)
        return response


class EnrollmentUpdateView(StaffRequiredMixin, UpdateView):
    """Изменение статуса записи (администратор)."""

    model = Enrollment
    form_class = EnrollmentForm
    template_name = "school/enrollment_form.html"

    def get_success_url(self):
        return reverse_lazy("school:enrollment_detail", kwargs={"pk": self.object.pk})


class EnrollmentDeleteView(StaffRequiredMixin, DeleteView):
    """Удаление записи (администратор)."""

    model = Enrollment
    context_object_name = "enrollment"
    template_name = "school/enrollment_confirm_delete.html"
    success_url = reverse_lazy("school:enrollment_list")


class EnrollmentCancelView(LoginRequiredMixin, View):
    """Отмена записи студентом."""

    def post(self, request, pk: int):
        enrollment = (
            Enrollment.objects.filter(pk=pk, user=request.user)
            .select_related("course")
            .first()
        )
        if not enrollment:
            return HttpResponseForbidden("Запись не найдена.")
        try:
            cancel_enrollment(request.user, enrollment)
        except Exception:
            return redirect("school:enrollment_detail", pk=pk)
        return redirect("school:course_list")


class EnrollmentFinishView(LoginRequiredMixin, View):
    """Завершение обучения по записи."""

    def post(self, request, pk: int):
        enrollment = Enrollment.objects.filter(pk=pk).select_related("user").first()
        if not enrollment:
            return HttpResponseForbidden("Запись не найдена.")
        if not (is_admin(request.user) or enrollment.user_id == request.user.id):
            return HttpResponseForbidden("Недостаточно прав.")
        if enrollment.status == "finished":
            return redirect("school:enrollment_detail", pk=pk)
        enrollment.status = "finished"
        enrollment.save(update_fields=["status"])
        log_action(request.user, "Завершение записи", "Enrollment", enrollment.pk)
        return redirect("school:enrollment_detail", pk=pk)


class SignUpView(CreateView):
    """Регистрация нового пользователя."""

    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
