from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify


class Category(models.Model):
    # Category name must be unique to avoid duplicates (e.g., Music, Sports)
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name"
    )

    # Slug is a URL-friendly version of the name (e.g., "business-corporate")
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Event(models.Model):

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    image = models.ImageField(
        upload_to="event_images/",
        blank=True,
        null=True,
    )

    date = models.DateTimeField()

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    max_tickets = models.PositiveIntegerField(
        default=1,
    )

    categories = models.ManyToManyField(
        Category,
        related_name="events",
        blank=True,
        db_table="event_category",
    )

    @property
    def category_label(self):
        names = self.categories.values_list("name", flat=True)
        return ", ".join(names) if names else "Uncategorized"

    def __str__(self):
        return self.title

    @property
    def serial_number(self):
        return f"#{self.pk}"

    @property
    def tickets_sold(self):
        from django.db.models import Sum
        bookings_count = self.bookings.count()
        tickets_count = self.tickets.aggregate(total=Sum('quantity'))['total'] or 0
        return bookings_count + tickets_count

    @property
    def tickets_remaining(self):
        return max(self.max_tickets - self.tickets_sold, 0)

    @property
    def revenue(self):
        return self.price * self.tickets_sold

    @property
    def is_sold_out(self):
        return self.tickets_remaining <= 0

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.date < timezone.now()



class Ticket(models.Model):
    """A ticket booked by an attendee for a specific event."""

    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='tickets',
    )
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets',
    )
    quantity = models.PositiveIntegerField(default=1)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ['-booked_at']

    def __str__(self):
        return f'{self.attendee} → {self.event} ({self.quantity})'


class EventBooking(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_bookings",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        unique_together = ("user", "event")
        ordering = ["-booked_at"]

    def __str__(self):
        return f"{self.user.username} → {self.event.title}"
