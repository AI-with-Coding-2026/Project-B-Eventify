from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify


class Category(models.Model):
    # Category name must be unique to avoid duplicates
    # Example: Music, Sports, Technology
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name"
    )

    # URL-friendly version of the category name
    # Example: "Business & Corporate" -> "business-corporate"
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
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


class Event(models.Model):

    # ---------------------------------------------------------
    # Legacy/default category choices
    # ---------------------------------------------------------
    # Keep these for compatibility with existing parts of the
    # project while the category system is being migrated to
    # the new Many-to-Many relationship.
    CATEGORY_CHOICES = [
        ("music", "Music"),
        ("sports", "Sports"),
        ("tech", "Tech"),
        ("arts", "Arts"),
        ("other", "Other"),
    ]

    # ---------------------------------------------------------
    # Organizer
    # ---------------------------------------------------------
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )

    # ---------------------------------------------------------
    # Event information
    # ---------------------------------------------------------
    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

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

    # ---------------------------------------------------------
    # NEW MANY-TO-MANY CATEGORY RELATIONSHIP
    # ---------------------------------------------------------
    #
    # One Event can have many Categories.
    # One Category can belong to many Events.
    #
    # Django will create a pivot/intermediate table:
    #
    # event_category
    #
    # containing approximately:
    #
    # event_id | category_id
    #
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="events",
        db_table="event_category",
    )

    # ---------------------------------------------------------
    # Custom category
    # ---------------------------------------------------------
    # Kept because the existing project already supports a
    # custom category when needed.
    custom_category = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Custom category",
    )

    # ---------------------------------------------------------
    # String representation
    # ---------------------------------------------------------
    def __str__(self):
        return self.title

    # ---------------------------------------------------------
    # Category choices
    # ---------------------------------------------------------
    @classmethod
    def get_all_category_choices(cls):
        """
        Return merged category choices:

        1. Built-in/default categories
        2. Categories created through the admin

        This method is kept temporarily for compatibility with
        existing forms/views that still use it.
        """

        seen = {
            slug
            for slug, _ in cls.CATEGORY_CHOICES
        }

        merged = list(cls.CATEGORY_CHOICES)

        for cat in Category.objects.all():
            if cat.slug not in seen:
                merged.insert(
                    -1,
                    (cat.slug, cat.name)
                )
                seen.add(cat.slug)

        return merged

    # ---------------------------------------------------------
    # Category label
    # ---------------------------------------------------------
    @property
    def category_label(self):
        """
        Return a readable category label.

        Since the event now supports multiple categories,
        return all assigned category names separated by commas.

        The custom category is included when present.
        """

        category_names = list(
            self.categories.values_list(
                "name",
                flat=True
            )
        )

        custom = (self.custom_category or "").strip()

        if custom:
            category_names.append(custom)

        if category_names:
            return ", ".join(category_names)

        return "Other"

    # ---------------------------------------------------------
    # Serial number
    # ---------------------------------------------------------
    @property
    def serial_number(self):
        return f"#{self.pk}"

    # ---------------------------------------------------------
    # Tickets sold
    # ---------------------------------------------------------
    @property
    def tickets_sold(self):
        bookings_count = self.bookings.count()

        tickets_count = (
            self.tickets.aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )

        return bookings_count + tickets_count

    # ---------------------------------------------------------
    # Tickets remaining
    # ---------------------------------------------------------
    @property
    def tickets_remaining(self):
        return max(
            self.max_tickets - self.tickets_sold,
            0
        )

    # ---------------------------------------------------------
    # Revenue
    # ---------------------------------------------------------
    @property
    def revenue(self):
        return self.price * self.tickets_sold

    # ---------------------------------------------------------
    # Sold out
    # ---------------------------------------------------------
    @property
    def is_sold_out(self):
        return self.tickets_remaining <= 0

    # ---------------------------------------------------------
    # Expired
    # ---------------------------------------------------------
    @property
    def is_expired(self):
        from django.utils import timezone

        return self.date < timezone.now()


class Ticket(models.Model):
    """
    A ticket booked by an attendee for a specific event.
    """

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("pending", "Pending"),
        ("cancelled", "Cancelled"),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    booked_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ["-booked_at"]

    def __str__(self):
        return (
            f"{self.attendee} → "
            f"{self.event} "
            f"({self.quantity})"
        )


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

    booked_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        unique_together = ("user", "event")
        ordering = ["-booked_at"]

    def __str__(self):
        return (
            f"{self.user.username} → "
            f"{self.event.title}"
        )