from django.db import models
from django.utils.text import slugify
from django.conf import settings

class Category(models.Model):
    # Category name must be unique to avoid duplicates (e.g., Music, Sports)
    name = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Category Name"
    )
    
    # Slug is a URL-friendly version of the name (e.g., "business-corporate")
    # It must be unique and can be left blank in forms as it generates automatically
    slug = models.SlugField(
        max_length=120, 
        unique=True, 
        blank=True
    )
    
    # Optional description to provide more context about the category
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Description"
    )
    
    # Automatically records the date and time when the category is created
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Created At"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']  # Automatically sorts categories alphabetically

    def __str__(self):
        # Displays the category name clearly in the admin panel and selections
        return self.name

    def save(self, *args, **kwargs):
        # If no slug is provided, automatically generate it from the category name
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


from django.db import models
from django.conf import settings


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
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )