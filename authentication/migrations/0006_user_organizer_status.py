from django.db import migrations, models


def approve_existing_organizers(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    User.objects.filter(role='organizer').update(organizer_status='approved')
    User.objects.exclude(role='organizer').update(organizer_status='not_required')


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_alter_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='organizer_status',
            field=models.CharField(
                choices=[
                    ('not_required', 'Not required'),
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('denied', 'Denied'),
                ],
                default='not_required',
                max_length=20,
            ),
        ),
        migrations.RunPython(
            approve_existing_organizers,
            migrations.RunPython.noop,
        ),
    ]
