from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from events.models import Event


class Booking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings_made",
    )
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-booked_at"]

    def __str__(self):
        return f"{self.quantity} ticket(s) for {self.event.title} ({self.customer_email})"