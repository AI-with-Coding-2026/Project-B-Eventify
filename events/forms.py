from django import forms

from .models import Event


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
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }

    def clean_poster(self):
        poster = self.cleaned_data.get("poster")

        if not poster:
            return poster

        # Existing poster during edit.
        # Do not revalidate it as a new upload.
        if not hasattr(poster, "content_type"):
            return poster

        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]

        if poster.content_type not in allowed_types:
            raise forms.ValidationError(
                "Only JPG, PNG, and WEBP images are allowed."
            )

        max_size = 5 * 1024 * 1024

        if poster.size > max_size:
            raise forms.ValidationError(
                "Poster image must be 5 MB or smaller."
            )

        return poster