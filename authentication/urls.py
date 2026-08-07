from django.urls import path

from . import views


urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/success/', views.register_success, name='register_success'),

    #templates pages
    path('', views.home, name='home'),
    
]

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


    # Role-based access control

    path(
        'unauthorized/',
        views.unauthorized,
        name='unauthorized'
    ),

    path(
        'dashboard/organizer/',
        views.organizer_dashboard,
        name='organizer_dashboard'
    ),

    path(
        'dashboard/attendee/',
        views.attendee_dashboard,
        name='attendee_dashboard'
    ),

]
