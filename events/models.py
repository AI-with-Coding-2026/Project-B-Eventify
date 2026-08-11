from django.conf import settings
from django.db import models


class Event(models.Model):
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    date = models.DateTimeField()

    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    max_tickets = models.PositiveIntegerField()

    poster = models.ImageField(
        upload_to="event_posters/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
