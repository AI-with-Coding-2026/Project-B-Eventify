from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return redirect("login")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_redirect, name="home"),
    path("accounts/", include("accounts.urls")),
]