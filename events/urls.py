from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path(
        'categories/create/',
        views.category_create,
        name='category_create',
    ),
    path('accounts/', include('authentication.urls')),
]