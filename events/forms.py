import os
from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

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
            'categories',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'categories': forms.CheckboxSelectMultiple(),
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

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date is not None:
            now = timezone.now()
            if date < now:
                raise ValidationError('Event date cannot be in the past.')
            max_date = now + timedelta(days=183)  # ~6 months
            if date > max_date:
                raise ValidationError(
                    'Event date cannot be more than 6 months from now.'
                )
        return date
