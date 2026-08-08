from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect

from .models import UserRole


def user_is_admin(user):
    """Return True only for active, authenticated Admin-role users."""
    return user.is_authenticated and user.is_active and user.is_admin


def _normalize_roles(roles):
    """Accept UserRole members or raw role strings."""
    normalized = []
    for role in roles:
        if isinstance(role, str):
            normalized.append(role)
        else:
            normalized.append(role.value if hasattr(role, "value") else role)
    return normalized


def role_required(*allowed_roles, login_url="login", redirect_url="unauthorized"):
    """
    Require an authenticated user with one of the given roles.
    """
    roles = _normalize_roles(allowed_roles)

    def decorator(view_func):
        @login_required(login_url=login_url)
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            return redirect(redirect_url)

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """Shortcut for views restricted to Admin users."""
    return role_required(UserRole.ADMIN)(view_func)


def organizer_required(view_func):
    """Shortcut for views restricted to Organizer users."""
    return role_required(UserRole.ORGANIZER)(view_func)


def attendee_required(view_func):
    """Shortcut for views restricted to Attendee users."""
    return role_required(UserRole.ATTENDEE)(view_func)