from django.db import models
from django.conf import settings

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    date = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_tickets = models.IntegerField()
    poster_image = models.ImageField(upload_to='event_posters/')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
