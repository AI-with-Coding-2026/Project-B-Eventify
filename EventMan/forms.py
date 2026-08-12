from django import forms
from PIL import Image

from .models import Event


class EventForm(forms.ModelForm):

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
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Event title',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Describe your event',
                    'rows': 5,
                }
            ),

            'location': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Event location',
                }
            ),

            'date': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                }
            ),

            'ticket_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '0.00',
                    'min': '0',
                    'step': '0.01',
                }
            ),

            'max_tickets': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Maximum tickets',
                    'min': '1',
                }
            ),

            'poster': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.jpg,.jpeg,.png,.webp',
                }
            ),
        }

    def clean_poster(self):
        poster = self.cleaned_data.get('poster')

        if not poster:
            return poster

        # Maximum file size: 5 MB
        max_size = 5 * 1024 * 1024

        if poster.size > max_size:
            raise forms.ValidationError(
                'Poster image must not be larger than 5 MB.'
            )

        # Verify that the uploaded file is actually a valid image.
        try:
            image = Image.open(poster)
            image.verify()
        except Exception:
            raise forms.ValidationError(
                'Please upload a valid image file.'
            )

        return poster