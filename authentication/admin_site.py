from django.contrib.admin import AdminSite
from django.shortcuts import redirect


class EventifyAdminSite(AdminSite):
    """Django admin site restricted to users with the Admin role."""

    site_header = 'Eventify Administration'
    site_title = 'Eventify Admin'
    index_title = 'Administrative Dashboard'

    def has_permission(self, request):
        """Vérifie si l'utilisateur est actif, connecté et possède le rôle admin."""
        return (
            request.user.is_active
            and request.user.is_authenticated
            and getattr(request.user, 'is_admin', False)
        )

    def admin_view(self, view, cacheable=False):
        """Redirige les utilisateurs connectés non autorisés vers la page 'unauthorized'."""
        inner = super().admin_view(view, cacheable=cacheable)

        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and not self.has_permission(request):
                return redirect('unauthorized')
            return inner(request, *args, **kwargs)

        return wrapper


# Instance unique du site d'administration
eventify_admin_site = EventifyAdminSite(name='eventify_admin')
