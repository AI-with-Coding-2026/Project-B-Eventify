from django.urls import path

from . import views


urlpatterns = [
    # Admin
    path(
        'admin/dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    # Registration
    path(
        'register/',
        views.register,
        name='register'
    ),
    path(
        'register/success/',
        views.register_success,
        name='register_success'
    ),

    # Home
    path(
        '',
        views.home,
        name='home'
    ),

    # Authentication
    path(
        'login/',
        views.login_view,
        name='login'
    ),
    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

    # Role-based access control
    path(
        'unauthorized/',
        views.unauthorized,
        name='unauthorized'
    ),
    path(
        'dashboard/organizer/',
        views.organizer_dashboard,
        name='organizer_dashboard'
    ),
    path(
        'dashboard/attendee/',
        views.attendee_dashboard,
        name='attendee_dashboard'
    ),
]