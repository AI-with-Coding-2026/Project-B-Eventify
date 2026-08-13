"""
URL configuration for omnistock project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from django.views.generic import RedirectView

from authentication.admin_site import eventify_admin_site
from authentication.views import admin_dashboard
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('authentication.urls')),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path(
        'admin/dashboard/',
        RedirectView.as_view(pattern_name='admin_dashboard', permanent=True),
    ),
    path('django-admin/', eventify_admin_site.urls),
    path('events/', include('events.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )