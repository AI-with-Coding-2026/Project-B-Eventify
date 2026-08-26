from django.db import migrations, models


def approve_existing_events(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    Event.objects.all().update(publish_status='approved')


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_widen_category_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='publish_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('denied', 'Denied'),
                ],
                default='approved',
                max_length=20,
            ),
        ),
        migrations.RunPython(approve_existing_events, migrations.RunPython.noop),
    ]
