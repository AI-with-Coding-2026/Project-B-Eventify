from django import forms

from .models import Event

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}

MAX_POSTER_SIZE_MB = 5
MAX_POSTER_SIZE_BYTES = MAX_POSTER_SIZE_MB * 1024 * 1024


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
            "poster",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean_poster(self):
        poster = self.cleaned_data.get("poster")

        # If no new file was uploaded (e.g. editing without replacing the
        # image), keep whatever is already on the instance.
        if not poster or not hasattr(poster, "content_type"):
            return poster

        if poster.content_type not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError(
                "Unsupported image type. Please upload a JPEG, PNG or WEBP file."
            )

        if poster.size > MAX_POSTER_SIZE_BYTES:
            raise forms.ValidationError(
                f"Image file is too large. Maximum allowed size is "
                f"{MAX_POSTER_SIZE_MB}MB."
            )

        return poster

    def clean_max_tickets(self):
        max_tickets = self.cleaned_data.get("max_tickets")

        if max_tickets is not None and max_tickets < 1:
            raise forms.ValidationError(
                "There must be at least 1 ticket available."
            )

        return max_tickets

    def clean_ticket_price(self):
        ticket_price = self.cleaned_data.get("ticket_price")

        if ticket_price is not None and ticket_price < 0:
            raise forms.ValidationError("Ticket price cannot be negative.")

        return ticket_price
