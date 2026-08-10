from django.contrib import admin
from authentication.admin_site import eventify_admin_site
from .models import Event


class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'date', 'ticket_price', 'max_tickets', 'created_at')
    list_filter = ('date', 'created_at', 'organizer')
    search_fields = ('title', 'description', 'location', 'organizer__username', 'organizer__email')
    ordering = ('-date',)


eventify_admin_site.register(Event, EventAdmin)
admin.site.register(Event, EventAdmin)
