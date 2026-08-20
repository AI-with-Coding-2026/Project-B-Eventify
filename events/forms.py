from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Event

MAX_UPLOAD_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "location",
            "date",
            "ticket_price",
            "max_tickets",
            "poster_image",
        ]
        widgets = {
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "poster_image":
                field.required = field.required  # keep model-derived requiredness
            field.widget.attrs.setdefault("class", "form-control")

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise ValidationError("Title is required.")
        return title

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < timezone.now():
            raise ValidationError("Event date cannot be in the past.")
        return date

    def clean_ticket_price(self):
        price = self.cleaned_data["ticket_price"]
        if price < 0:
            raise ValidationError("Ticket price cannot be negative.")
        return price

    def clean_max_tickets(self):
        max_tickets = self.cleaned_data["max_tickets"]
        if max_tickets < 1:
            raise ValidationError("Maximum tickets must be at least 1.")
        return max_tickets

    def clean_poster_image(self):
        image = self.cleaned_data.get("poster_image")
        # Only validate when a *new* file was actually uploaded in this request.
        if image and hasattr(image, "content_type"):
            if image.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError(
                    "Unsupported file type. Please upload a JPEG, PNG, or WEBP image."
                )
            if image.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise ValidationError(
                    f"Image file is too large (max {MAX_UPLOAD_SIZE_MB}MB)."
                )
        return image
