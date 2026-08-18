from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def organizer_required(view_func):
    """Restrict a view to authenticated users with the organizer role."""

    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if request.user.role != request.user.Role.ORGANIZER:
            messages.error(
                request,
                "You need an organizer account to access that page.",
            )
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)

    return wrapped_view
