from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Course, Enrollment


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "category",
            "teacher",
            "image",
            "start_date",
            "end_date",
            "price",
            "level",
            "is_published",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ограничиваем список преподавателей только пользователями с ролью "Преподаватель"
        self.fields["teacher"].queryset = User.objects.filter(
            roles__name__iexact="Преподаватель"
        )
        self.fields["teacher"].label_from_instance = (
            lambda user: f"{user.first_name} {user.last_name}".strip() or user.username
        )


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["user", "course", "status"]


class EnrollmentCreateForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["course"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_course(self):
        course = self.cleaned_data.get("course")
        if self.user and course:
            if Enrollment.objects.filter(user=self.user, course=course).exists():
                raise forms.ValidationError("Вы уже записаны на этот курс.")
        return course


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]
