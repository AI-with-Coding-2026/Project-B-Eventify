from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import UserRole


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Class-based view mixin that requires authentication and an allowed role.

    Admin users always have full access. Unauthorized users receive 403 Forbidden.

    Usage:
        class OrganizerDashboardView(RoleRequiredMixin, TemplateView):
            allowed_roles = (UserRole.ORGANIZER,)
            template_name = 'authentication/organizer_dashboard.html'
    """

    allowed_roles = ()
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user_role = request.user.role
        if user_role != UserRole.ADMIN and user_role not in self.allowed_roles:
            raise PermissionDenied

        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs
        )