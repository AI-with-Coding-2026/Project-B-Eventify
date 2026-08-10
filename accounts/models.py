from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ORGANIZER = "organizer", "Organizer"
        ATTENDEE = "attendee", "Attendee"

    # Remove Django's original username field.
    username = None

    email = models.EmailField(
        unique=True,
        help_text="The email address used to log in.",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ATTENDEE,
    )

    # Django will authenticate users with email.
    USERNAME_FIELD = "email"

    # These fields are requested by createsuperuser in addition to email.
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        name = self.get_full_name().strip()
        return name or self.email