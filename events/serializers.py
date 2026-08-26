from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    category_label = serializers.ReadOnlyField()
    serial_number = serializers.ReadOnlyField()
    tickets_sold = serializers.ReadOnlyField()
    tickets_remaining = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = [
            "id",
            "serial_number",
            "title",
            "description",
            "location",
            "image",
            "date",
            "price",
            "max_tickets",
            "category",
            "category_label",
            "custom_category",
            "organizer",
            "tickets_sold",
            "tickets_remaining",
            "is_sold_out",
            "is_expired",
        ]