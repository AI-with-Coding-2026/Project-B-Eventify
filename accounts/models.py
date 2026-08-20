from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    is_organizer = models.BooleanField(default=True)

    def __str__(self):
        role = "organizer" if self.is_organizer else "attendee"
        return f"{self.user.username} ({role})"