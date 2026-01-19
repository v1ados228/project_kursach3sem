import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Course, Enrollment


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            return name
        if any(char.isdigit() for char in name):
            raise forms.ValidationError("Название категории не должно содержать цифры.")
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\s\-]+", name):
            raise forms.ValidationError("Название категории содержит недопустимые символы.")
        banned = {"пакость", "ругательство", "спам"}
        if any(word in name.lower() for word in banned):
            raise forms.ValidationError("Введенное содержит недопустимую лексику.")
        queryset = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Категория с таким названием уже существует.")
        return name


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

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            return title
        if any(char.isdigit() for char in title):
            raise forms.ValidationError("Название курса не должно содержать цифры.")
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\s\-:]+", title):
            raise forms.ValidationError("Название курса содержит недопустимые символы.")
        banned = {"пакость", "ругательство", "спам"}
        if any(word in title.lower() for word in banned):
            raise forms.ValidationError("Введенное содержит недопустимую лексику.")
        category = self.cleaned_data.get("category")
        if category:
            queryset = Course.objects.filter(category=category, title__iexact=title)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError("Название курса должно быть уникальным в категории.")
        return title

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        price = cleaned.get("price")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Дата старта не может быть позже даты окончания.")
        if price is not None and price <= 0:
            raise forms.ValidationError("Цена должна быть положительной.")
        return cleaned


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
