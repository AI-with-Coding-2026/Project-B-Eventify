from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/success/', views.register_success, name='register_success'),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),
    path(
        'dashboard/organizer/',
        views.organizer_dashboard,
        name='organizer_dashboard',
    ),
    path(
        'dashboard/attendee/',
        views.attendee_dashboard,
        name='attendee_dashboard',
    ),
    path(
        'dashboard/attendee/my-bookings/',
        views.my_bookings,
        name='my_bookings',
    ),
    path(
        'dashboard/attendee/bookings/<int:pk>/cancel/',
        views.cancel_booking,
        name='cancel_booking',
    ),
]