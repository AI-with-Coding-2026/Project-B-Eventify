from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import dashboard_view, register_view


urlpatterns = [
    path(
        "register/",
        register_view,
        name="register",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "dashboard/",
        dashboard_view,
        name="dashboard",
    ),
]