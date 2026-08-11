from django.db import models
from django.conf import settings

class Event(models.Model):
    CURRENCY_CHOICES = [
        ('USD', '$ USD - US Dollar'),
        ('EUR', '€ EUR - Euro'),
        ('TRY', '₺ TRY - Turkish Lira'),
        ('GBP', '£ GBP - British Pound'),
        ('JPY', '¥ JPY - Japanese Yen'),
        ('CAD', 'C$ CAD - Canadian Dollar'),
        ('AUD', 'A$ AUD - Australian Dollar'),
    ]

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    date = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    max_tickets = models.PositiveIntegerField()
    
    poster = models.ImageField(upload_to='event_posters/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_currency_symbol(self):
        symbols = {
            'USD': '$',
            'EUR': '€',
            'TRY': '₺',
            'GBP': '£',
            'JPY': '¥',
            'CAD': 'C$',
            'AUD': 'A$',
        }
        return symbols.get(self.currency, self.currency)