from django.db import models

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('music', 'Music'),
        ('sports', 'Sports'),
        ('tech', 'Tech'),
        ('arts', 'Arts'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    date = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')

    def __str__(self):
        return self.title