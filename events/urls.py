from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path(
        'categories/',
        views.category_list,
        name='category_list',
    ),
    path(
        'categories/create/',
        views.category_create,
        name='category_create',
    ),
    # Edit/update an existing category
    # URL example: /events/categories/1/edit/
    path(
        'categories/<int:pk>/edit/',
        views.category_update,
        name='category_update',
    ),
    path(
        'categories/<int:pk>/delete/',
        views.category_delete,
        name='category_delete',
    ),
]
