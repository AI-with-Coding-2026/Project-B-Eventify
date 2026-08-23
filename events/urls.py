from django.urls import path
from . import views

urlpatterns = [
    path('', views.organizer_event_list, name='organizer_event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('<int:pk>/book/', views.book_event, name='book_event'),
]
