from django.urls import path
from . import views

urlpatterns = [
    path('events/', views.event_list, name='event_list'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('my-events/', views.my_events, name='my_events'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:pk>/delete/', views.delete_event, name='delete_event'),
]