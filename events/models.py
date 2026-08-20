from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def event_poster_upload_path(instance, filename):
    """Store posters under media/event_posters/<organizer_id>/<filename>."""
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
    date = models.DateTimeField(help_text="Date and time the event takes place")
    ticket_price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    max_tickets = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    poster_image = models.ImageField(
        upload_to=event_poster_upload_path, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        # Remove the stored poster file (if any) along with the DB row.
        if self.poster_image:
            self.poster_image.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def tickets_sold(self):
        return self.bookings.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def tickets_remaining(self):
        return max(self.max_tickets - self.tickets_sold, 0)

    @property
    def revenue(self):
        return self.ticket_price * self.tickets_sold
