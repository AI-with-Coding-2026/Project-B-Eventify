from django.urls import path

from . import views

urlpatterns = [
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register/', views.register, name='register'),
    path('register/success/', views.register_success, name='register_success'),
]
