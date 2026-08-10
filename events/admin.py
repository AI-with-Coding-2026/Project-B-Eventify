from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'date',
        'location',
        'organizer',
    )

    search_fields = (
        'title',
        'location',
        'organizer__username',
    )

    list_filter = (
        'date',
        'location',
    )