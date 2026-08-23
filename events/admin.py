from django.contrib import admin
from authentication.admin_site import eventify_admin_site
from .models import Booking, Event


class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'date', 'ticket_price', 'max_tickets', 'created_at')
    list_filter = ('date', 'created_at', 'organizer')
    search_fields = ('title', 'description', 'location', 'organizer__username', 'organizer__email')
    ordering = ('-date',)


class BookingAdmin(admin.ModelAdmin):
    list_display = ('event', 'attendee', 'quantity', 'booked_at')
    list_filter = ('booked_at', 'event')
    search_fields = ('event__title', 'attendee__username', 'attendee__email')
    ordering = ('-booked_at',)


eventify_admin_site.register(Event, EventAdmin)
eventify_admin_site.register(Booking, BookingAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Booking, BookingAdmin)
