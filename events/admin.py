from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "location", "date", "ticket_price", "max_tickets")
    list_filter = ("organizer", "date")
    search_fields = ("title", "location")
