from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .models import UserRole


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Class-based view mixin that requires authentication and an allowed role.

    Usage:
        class OrganizerDashboardView(RoleRequiredMixin, TemplateView):
            allowed_roles = (UserRole.ORGANIZER,)
            template_name = 'authentication/organizer_dashboard.html'
    """
    allowed_roles = ()
    login_url = 'login'
    redirect_url = 'unauthorized'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles:
            return redirect(self.redirect_url)
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
