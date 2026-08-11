from django.urls import path

from . import views


urlpatterns = [
    path(
        'categories/create/',
        views.category_create,
        name='category_create',
    ),
]