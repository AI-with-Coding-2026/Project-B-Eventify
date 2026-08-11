from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrganizerEventListView.as_view(), name='dashboard'),
    path('create/', views.EventCreateView.as_view(), name='event_create'),
    path('<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_edit'),
    path('<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
]
