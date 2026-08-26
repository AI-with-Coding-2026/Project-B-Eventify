from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify


class EventPublishStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    DENIED = 'denied', 'Denied'


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
    CATEGORY_CHOICES = [
        ("music", "Music"),
        ("sports", "Sports"),
        ("tech", "Tech"),
        ("arts", "Arts"),
        ("other", "Other"),
    ]

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

    category = models.CharField(
        max_length=120,
        default="other",
    )

    custom_category = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Custom category",
    )
    publish_status = models.CharField(
        max_length=20,
        choices=EventPublishStatus.choices,
        default=EventPublishStatus.APPROVED,
    )

    def __str__(self):
        return self.title

    @classmethod
    def get_all_category_choices(cls):
        """Return merged category choices: hardcoded defaults + admin-created.

        Admin-created Category entries are appended after the built-in
        choices, de-duplicated by slug so the list stays clean.
        """
        seen = {slug for slug, _ in cls.CATEGORY_CHOICES}
        merged = list(cls.CATEGORY_CHOICES)
        for cat in Category.objects.all():
            if cat.slug not in seen:
                merged.insert(-1, (cat.slug, cat.name))  # before "Other"
                seen.add(cat.slug)
        return merged

    @property
    def category_label(self):
        custom = (self.custom_category or "").strip()
        if self.category == "other" and custom:
            return custom
        # Check hardcoded choices first.
        for slug, label in self.CATEGORY_CHOICES:
            if slug == self.category:
                return label
        # Then check admin-created categories.
        try:
            return Category.objects.get(slug=self.category).name
        except Category.DoesNotExist:
            return self.category.replace("-", " ").title() if self.category else "Other"

    @property
    def serial_number(self):
        return f"#{self.pk}"

    @property
    def tickets_sold(self):
        from django.db.models import Sum
        legacy_bookings = self.bookings.exclude(
            user__in=self.tickets.values_list('attendee_id', flat=True)
        ).count()
        tickets_count = self.tickets.aggregate(total=Sum('quantity'))['total'] or 0
        return legacy_bookings + tickets_count

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

    @property
    def is_published(self):
        return self.publish_status == EventPublishStatus.APPROVED

    @property
    def is_pending_publish(self):
        return self.publish_status == EventPublishStatus.PENDING

    @property
    def is_denied_publish(self):
        return self.publish_status == EventPublishStatus.DENIED


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

    @property
    def user(self):
        return self.attendee


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

    @property
    def attendee(self):
        return self.user

    @property
    def quantity(self):
        return 1


def get_attendee_cancellable_booking(user, pk):
    """Return a Ticket or legacy EventBooking owned by this attendee."""
    ticket = (
        Ticket.objects.filter(pk=pk, attendee=user)
        .select_related('event', 'attendee')
        .first()
    )
    if ticket is not None:
        return ticket
    return (
        EventBooking.objects.filter(pk=pk, user=user)
        .select_related('event', 'user')
        .first()
    )


# =========================================================
# 🎯 TASK 3: Real-Time Notification Storage Model
# =========================================================

class Notification(models.Model):
    """Model to log real-time booking and cancellation events for organizers."""
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    event = models.ForeignKey(
        Event, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username} - {self.title}"
