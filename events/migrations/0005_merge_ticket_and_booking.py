# Merge Ahmed ticket booking with admin-dashboard EventBooking history.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_add_ticket_booking'),
        ('events', '0004_eventbooking'),
    ]

    operations = []
