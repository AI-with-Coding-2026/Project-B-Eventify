# Merge Ahmed ticket history with ritvik-new booking/admin history.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_add_ticket_booking'),
        ('events', '0005_ticket_verbose_name'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventbooking',
            options={
                'ordering': ['-booked_at'],
                'verbose_name': 'Booking',
                'verbose_name_plural': 'Bookings',
            },
        ),
        migrations.AlterModelOptions(
            name='ticket',
            options={
                'ordering': ['-booked_at'],
                'verbose_name': 'Ticket',
                'verbose_name_plural': 'Tickets',
            },
        ),
    ]
