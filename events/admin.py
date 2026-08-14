from django.contrib import admin
from authentication.admin_site import eventify_admin_site
from .models import Event, Category, EventBooking

# Register Event model using custom admin site
eventify_admin_site.register(Event)


class EventBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'booked_at')
    list_filter = ('booked_at',)
    search_fields = ('user__username', 'event__title')
    ordering = ('-booked_at',)


eventify_admin_site.register(EventBooking, EventBookingAdmin)

# Register Category model using standard admin decorator
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}