from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()
    tickets_available = serializers.IntegerField(
        source="tickets_remaining",
        read_only=True,
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "date",
            "price",
            "max_tickets",
            "tickets_available",
            "categories",
            "image",
        ]

    def get_categories(self, obj):
        return [
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
            }
            for category in obj.categories.all()
        ]
