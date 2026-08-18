# Generated manually to mirror `manage.py makemigrations events`.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import events.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('location', models.CharField(max_length=255)),
                ('date', models.DateTimeField(help_text='Date and time the event takes place.')),
                ('ticket_price', models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(0)])),
                ('max_tickets', models.PositiveIntegerField(help_text='Maximum number of tickets available for this event.', validators=[django.core.validators.MinValueValidator(1)])),
                ('poster', models.ImageField(help_text='Poster image for the event (JPEG, PNG or WEBP, max 5MB).', upload_to=events.models.poster_upload_path)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organizer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
    ]
