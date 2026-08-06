from django.urls import path

from . import views


urlpatterns = [

    # Person 1: Registration

    path(
        'register/',
        views.register,
        name='register'
    ),

    path(
        'register/success/',
        views.register_success,
        name='register_success'
    ),


    # Person 2: Authentication

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

]