from django.db import migrations, models
from django.utils.text import slugify


def forward_migrate_categories(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    Category = apps.get_model('events', 'Category')

    for event in Event.objects.all():
        old_cat = getattr(event, 'category', None)
        if old_cat:
            cat_slug = slugify(old_cat)
            if not cat_slug:
                continue
            cat_name = old_cat.replace('-', ' ').title()

            cat_obj = Category.objects.filter(slug=cat_slug).first()
            if not cat_obj:
                cat_obj = Category.objects.filter(name__iexact=cat_name).first()
            if not cat_obj:
                cat_obj = Category.objects.create(name=cat_name, slug=cat_slug)

            event.categories.add(cat_obj)


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_widen_category_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='categories',
            field=models.ManyToManyField(blank=True, db_table='event_category', related_name='events', to='events.category'),
        ),
        migrations.RunPython(
            forward_migrate_categories,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RemoveField(
            model_name='event',
            name='category',
        ),
    ]

