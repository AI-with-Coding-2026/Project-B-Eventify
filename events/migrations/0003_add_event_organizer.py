# Generated manually for organizer ownership on Event

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0002_alter_category_options_alter_category_created_at_and_more'),
    ]

    operations = [
        # Existing events have no owner; clear them before requiring organizer.
        migrations.RunSQL('DELETE FROM events_event;', migrations.RunSQL.noop),
        migrations.AddField(
            model_name='event',
            name='organizer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='events',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
