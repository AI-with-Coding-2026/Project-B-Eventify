from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event",
        "attendee",
        "quantity",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "event",
        "created_at",
    )

    search_fields = (
        "event__title",
        "attendee__username",
        "attendee__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)