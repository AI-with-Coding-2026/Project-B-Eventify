from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .decorators import _normalize_roles
from .models import UserRole


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Class-based view mixin that requires authentication and an allowed role.

    Admin users always have full access. Unauthorized authenticated users are
    redirected to the shared /unauthorized/ page (HTTP 403).

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
        allowed = _normalize_roles(self.allowed_roles)
        if user_role != UserRole.ADMIN and user_role not in allowed:
            return redirect('unauthorized')

        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
