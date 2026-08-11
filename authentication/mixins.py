from django.contrib.auth.mixins import LoginRequiredMixin
<<<<<<< HEAD
from django.shortcuts import redirect
=======
from django.core.exceptions import PermissionDenied
>>>>>>> origin/main

from .models import UserRole


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Class-based view mixin that requires authentication and an allowed role.

<<<<<<< HEAD
=======
    Admin users always have full access. Unauthorized users receive 403 Forbidden.

>>>>>>> origin/main
    Usage:
        class OrganizerDashboardView(RoleRequiredMixin, TemplateView):
            allowed_roles = (UserRole.ORGANIZER,)
            template_name = 'authentication/organizer_dashboard.html'
    """
    allowed_roles = ()
    login_url = 'login'
<<<<<<< HEAD
    redirect_url = 'unauthorized'
=======
>>>>>>> origin/main

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
<<<<<<< HEAD
        if request.user.role not in self.allowed_roles:
            return redirect(self.redirect_url)
=======
        user_role = request.user.role
        if user_role != UserRole.ADMIN and user_role not in self.allowed_roles:
            raise PermissionDenied
>>>>>>> origin/main
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
