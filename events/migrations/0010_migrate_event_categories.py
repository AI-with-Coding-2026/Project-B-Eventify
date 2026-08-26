from django.db import migrations
from django.utils.text import slugify


def migrate_categories_forward(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Category = apps.get_model("events", "Category")

    built_in_names = {
        "music": "Music",
        "sports": "Sports",
        "tech": "Tech",
        "arts": "Arts",
        "other": "Other",
    }

    for event in Event.objects.all():
        old_category = (event.category or "other").strip()
        custom_category = (event.custom_category or "").strip()

        if old_category == "other" and custom_category:
            category_name = custom_category
            category_slug = slugify(custom_category)
        else:
            category_name = built_in_names.get(
                old_category,
                old_category.replace("-", " ").title(),
            )
            category_slug = slugify(old_category)

        # Safety fallback in case slugify produces an empty string
        if not category_slug:
            category_slug = "other"

        category, created = Category.objects.get_or_create(
            slug=category_slug,
            defaults={
                "name": category_name,
            },
        )

        event.categories.add(category)


def migrate_categories_backward(apps, schema_editor):
    """
    Reverse migration intentionally does nothing.

    The old category/custom_category fields still exist at this stage,
    so reversing the many-to-many data migration does not need to
    overwrite them.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0009_event_categories"),
    ]

    operations = [
        migrations.RunPython(
            migrate_categories_forward,
            migrate_categories_backward,
        ),
    ]