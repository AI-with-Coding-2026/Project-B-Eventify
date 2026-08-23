import os
from django.conf import settings
from django.db import models


class Event(models.Model):
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    date = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_tickets = models.PositiveIntegerField()
    poster = models.ImageField(upload_to='event_posters/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} by {self.organizer.username}"

    def delete(self, *args, **kwargs):
        """Clean up poster file from disk when event instance is deleted."""
        if self.poster and hasattr(self.poster, 'path'):
            try:
                if os.path.isfile(self.poster.path):
                    os.remove(self.poster.path)
            except Exception:
                pass
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Remove old poster file when poster image is replaced or cleared."""
        if self.pk:
            try:
                old_instance = Event.objects.get(pk=self.pk)
                if old_instance.poster and old_instance.poster != self.poster:
                    if hasattr(old_instance.poster, 'path') and os.path.isfile(old_instance.poster.path):
                        os.remove(old_instance.poster.path)
            except Event.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class Booking(models.Model):
    """Records a ticket purchase by an attendee for a specific event."""
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    quantity = models.PositiveIntegerField(default=1)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booked_at']

    def __str__(self):
        return f"{self.attendee.username} \u00d7 {self.quantity} for {self.event.title}"
