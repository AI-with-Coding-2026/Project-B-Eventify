import os
from django import forms
from django.core.exceptions import ValidationError

from .models import Event

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class EventForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            },
            format='%Y-%m-%dT%H:%M',
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'],
        label='Event Date & Time',
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'description',
            'location',
            'date',
            'ticket_price',
            'max_tickets',
            'poster',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_poster(self):
        poster = self.cleaned_data.get('poster')
        if poster and hasattr(poster, 'size'):
            # Validate size
            if poster.size > MAX_FILE_SIZE_BYTES:
                raise ValidationError(
                    f'File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB.'
                )

            # Validate extension
            ext = os.path.splitext(poster.name)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                allowed_str = ', '.join(ALLOWED_IMAGE_EXTENSIONS)
                raise ValidationError(
                    f'Unsupported file format "{ext}". Allowed formats are: {allowed_str}.'
                )

        return poster

    def clean_ticket_price(self):
        price = self.cleaned_data.get('ticket_price')
        if price is not None and price < 0:
            raise ValidationError('Ticket price cannot be negative.')
        return price

    def clean_max_tickets(self):
        max_t = self.cleaned_data.get('max_tickets')
        if max_t is not None and max_t <= 0:
            raise ValidationError('Maximum tickets must be greater than zero.')
        return max_t
