# Generated manually for organizer ownership on Event

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0002_alter_category_options_alter_category_created_at_and_more'),
    ]

    operations = [
        # Organizer is added by 0003_event_location_event_max_tickets_event_organizer
        # when both histories are merged. Keep this migration for Ticket dependency.
    ]
