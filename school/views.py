from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CategoryForm, CourseForm, EnrollmentForm
from .models import Category, Course, Enrollment


class CategoryListView(ListView):
    model = Category
    template_name = "school/category_list.html"
    context_object_name = "categories"


class CategoryDetailView(DetailView):
    model = Category
    template_name = "school/category_detail.html"
    context_object_name = "category"


class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"
    success_url = reverse_lazy("school:category_list")


class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "school/category_form.html"

    def get_success_url(self):
        return reverse_lazy("school:category_detail", kwargs={"pk": self.object.pk})


class CategoryDeleteView(DeleteView):
    model = Category
    context_object_name = "category"
    template_name = "school/category_confirm_delete.html"
    success_url = reverse_lazy("school:category_list")


class CourseListView(ListView):
    model = Course
    template_name = "school/course_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        return Course.objects.select_related("category", "teacher").order_by("-created_at")


class CourseDetailView(DetailView):
    model = Course
    template_name = "school/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enrollments"] = (
            self.object.enrollment_set.select_related("user").order_by("-enrolled_at")
        )
        return context


class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"
    success_url = reverse_lazy("school:course_list")


class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "school/course_form.html"

    def get_success_url(self):
        return reverse_lazy("school:course_detail", kwargs={"pk": self.object.pk})


class CourseDeleteView(DeleteView):
    model = Course
    context_object_name = "course"
    template_name = "school/course_confirm_delete.html"
    success_url = reverse_lazy("school:course_list")


class EnrollmentListView(ListView):
    model = Enrollment
    template_name = "school/enrollment_list.html"
    context_object_name = "enrollments"

    def get_queryset(self):
        return (
            Enrollment.objects.select_related("user", "course", "course__category")
            .order_by("-enrolled_at")
        )


class EnrollmentDetailView(DetailView):
    model = Enrollment
    template_name = "school/enrollment_detail.html"
    context_object_name = "enrollment"


class EnrollmentCreateView(CreateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = "school/enrollment_form.html"
    success_url = reverse_lazy("school:enrollment_list")


class EnrollmentUpdateView(UpdateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = "school/enrollment_form.html"

    def get_success_url(self):
        return reverse_lazy("school:enrollment_detail", kwargs={"pk": self.object.pk})


class EnrollmentDeleteView(DeleteView):
    model = Enrollment
    context_object_name = "enrollment"
    template_name = "school/enrollment_confirm_delete.html"
    success_url = reverse_lazy("school:enrollment_list")


