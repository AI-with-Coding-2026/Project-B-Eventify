from .models import Profile


def profile(request):
    if request.user.is_authenticated:
        user_profile, _ = Profile.objects.get_or_create(
            user=request.user, defaults={"is_organizer": True}
        )
        return {"user_profile": user_profile}
    return {}