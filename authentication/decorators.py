from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import UserRole


def user_is_admin(user):
    """Return True only for active, authenticated Admin-role users."""
    return (
        user.is_authenticated
        and user.is_active
        and user.is_admin
    )


def _normalize_roles(roles):
    """Accept UserRole members or raw role strings."""
    normalized = []

    for role in roles:
        if isinstance(role, str):
            normalized.append(role)
        else:
            normalized.append(
                role.value if hasattr(role, "value") else role
            )

    return normalized


def role_required(*allowed_roles, login_url='login'):
    """
    Require an authenticated user with one of the given roles.

    Admin users always have full access, regardless of the required role.
    Unauthorized authenticated users receive HTTP 403 Forbidden.
    """
    roles = _normalize_roles(allowed_roles)

    def decorator(view_func):
        @login_required(login_url=login_url)
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_role = request.user.role
            if user_role == UserRole.ADMIN or user_role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """Restrict a view to Admin users."""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                request.get_full_path(),
                login_url="login",
            )

        if request.user.role == UserRole.ADMIN:
            return view_func(request, *args, **kwargs)

        return redirect('unauthorized')

    return wrapped_view


def organizer_required(view_func):
    """Shortcut for views restricted to Organizer users."""
    return role_required(UserRole.ORGANIZER)(view_func)


def attendee_required(view_func):
    """Shortcut for views restricted to Attendee users."""
    return role_required(UserRole.ATTENDEE)(view_func)
