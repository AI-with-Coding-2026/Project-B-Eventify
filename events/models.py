from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def poster_upload_path(instance, filename):
    return f"event_posters/{instance.organizer_id}/{filename}"


class Event(models.Model):
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    location = models.CharField(max_length=255)

    date = models.DateTimeField(
        help_text="Date and time the event takes place.",
    )

    ticket_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    max_tickets = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Maximum number of tickets available for this event.",
    )

    poster = models.ImageField(
        upload_to=poster_upload_path,
        help_text="Poster image for the event (JPEG, PNG or WEBP, max 5MB).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.title
