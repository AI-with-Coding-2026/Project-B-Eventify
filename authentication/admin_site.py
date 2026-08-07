from django.contrib.admin import AdminSite


class EventifyAdminSite(AdminSite):
    """Django admin site restricted to users with the Admin role."""

    site_header = 'Eventify Administration'
    site_title = 'Eventify Admin'
    index_title = 'Administrative Dashboard'

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_authenticated
            and request.user.is_admin
        )


eventify_admin_site = EventifyAdminSite(name='eventify_admin')
