from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from authentication.admin_site import eventify_admin_site
from authentication.views import admin_dashboard

urlpatterns = [
    path('', include('authentication.urls')),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path(
        'admin/dashboard/',
        RedirectView.as_view(pattern_name='admin_dashboard', permanent=True),
    ),
    path('django-admin/', eventify_admin_site.urls),
    path('events/', include('events.urls')),
    path('students/', include('students.urls')),
]

# تمكين عرض ملفات الصور والميديا في جميع البيئات
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
