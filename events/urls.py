from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path(
        'categories/create/',
        views.category_create,
        name='category_create',
    ),
    path(
        '<int:event_id>/book/',
        views.book_event,
        name='event_book',
    ),
    path(
        'my-bookings/',
        views.my_bookings,
        name='my_bookings',
    ),
]