from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("event", "customer_name", "customer_email", "quantity", "booked_at")
    list_filter = ("event",)
    search_fields = ("customer_name", "customer_email")
