from django.conf import settings
from django.contrib.auth.decorators import user_passes_test


def user_is_admin(user):
    """Return True only for active, authenticated Admin-role users."""
    return user.is_authenticated and user.is_active and user.is_admin


admin_required = user_passes_test(
    user_is_admin,
    login_url=settings.LOGIN_URL,
)
