from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    CategoryForm,
    CourseForm,
    EnrollmentCreateForm,
    EnrollmentForm,
    SignUpForm,
)
from .models import Category, Course, Enrollment


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class CategoryListView(ListView):
    model = Category
    template_name = "school/category_list.html"
    context_object_name = "categories"
    paginate_by = 9


class CategoryDetailView(DetailView):
    model = Category
    template_name = "school/category_detail.html"
    context_object_name = "category"


class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"
    success_url = reverse_lazy("school:category_list")


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"

    def get_success_url(self):
        return reverse_lazy("school:category_detail", kwargs={"pk": self.object.pk})


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    context_object_name = "category"
    template_name = "school/category_confirm_delete.html"
    success_url = reverse_lazy("school:category_list")


class CourseDetailView(DetailView):
    model = Course
    template_name = "school/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_staff or self.object.teacher_id == self.request.user.id:
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
    model = Course
    template_name = "school/course_list.html"
    context_object_name = "courses"
    paginate_by = 6

    def get_queryset(self):
        queryset = Course.objects.select_related("category", "teacher").order_by("-created_at")
        category_id = self.request.GET.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.order_by("name")
        context["selected_category"] = self.request.GET.get("category", "")
        return context


class CourseCreateView(StaffRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"
    success_url = reverse_lazy("school:course_list")


class CourseUpdateView(StaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"

    def get_success_url(self):
        return reverse_lazy("school:course_detail", kwargs={"pk": self.object.pk})


class CourseDeleteView(StaffRequiredMixin, DeleteView):
    model = Course
    context_object_name = "course"
    template_name = "school/course_confirm_delete.html"
    success_url = reverse_lazy("school:course_list")


class EnrollmentListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = "school/enrollment_list.html"
    context_object_name = "enrollments"
    paginate_by = 10

    def get_queryset(self):
        queryset = Enrollment.objects.select_related("user", "course", "course__category")
        if self.request.user.is_staff:
            return queryset.order_by("-enrolled_at")
        return queryset.filter(
            models.Q(user=self.request.user) | models.Q(course__teacher=self.request.user)
        ).order_by("-enrolled_at")


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = "school/enrollment_detail.html"
    context_object_name = "enrollment"

    def get_queryset(self):
        queryset = Enrollment.objects.select_related("user", "course", "course__category")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(
            models.Q(user=self.request.user) | models.Q(course__teacher=self.request.user)
        )


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
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
        return super().form_valid(form)


class EnrollmentUpdateView(StaffRequiredMixin, UpdateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = "school/enrollment_form.html"

    def get_success_url(self):
        return reverse_lazy("school:enrollment_detail", kwargs={"pk": self.object.pk})


class EnrollmentDeleteView(StaffRequiredMixin, DeleteView):
    model = Enrollment
    context_object_name = "enrollment"
    template_name = "school/enrollment_confirm_delete.html"
    success_url = reverse_lazy("school:enrollment_list")


class EnrollmentCancelView(LoginRequiredMixin, DeleteView):
    model = Enrollment
    template_name = "school/enrollment_confirm_delete.html"
    success_url = reverse_lazy("school:course_list")

    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)


class EnrollmentFinishView(LoginRequiredMixin, View):
    def post(self, request, pk):
        enrollment = Enrollment.objects.filter(pk=pk).select_related("user").first()
        if not enrollment:
            return HttpResponseForbidden("Запись не найдена.")
        if not (request.user.is_staff or enrollment.user_id == request.user.id):
            return HttpResponseForbidden("Недостаточно прав.")
        if enrollment.status == "finished":
            return redirect("school:enrollment_detail", pk=pk)
        enrollment.status = "finished"
        enrollment.save(update_fields=["status"])
        return redirect("school:enrollment_detail", pk=pk)


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
