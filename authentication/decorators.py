from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def admin_required(view_func):
    """
    Allow access only to admin users.
    Non-admin users are redirected to the custom admin login page.
    """

    @wraps(view_func)
    @login_required(login_url='eventify_admin:login')
    def wrapper(request, *args, **kwargs):

        if not request.user.is_admin:
            login_url = reverse('eventify_admin:login')

            return redirect(
                f'{login_url}?next={request.path}'
            )

        return view_func(request, *args, **kwargs)

    return wrapper