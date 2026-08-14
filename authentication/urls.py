from django.urls import path

from . import views


urlpatterns = [
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/students/', views.student_list, name='student_list'),
    path('admin/students/<int:pk>/', views.student_detail, name='student_detail'),
    path('admin/students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('admin/students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('register/', views.register, name='register'),
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
]

