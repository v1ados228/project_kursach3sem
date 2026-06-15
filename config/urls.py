"""Корневые URL проекта."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("school.urls")),
    path("api/", include("school.api_urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("oauth/", include("social_django.urls", namespace="social")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
