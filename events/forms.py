from django import forms
from .models import Event
from django.core.exceptions import ValidationError

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'location', 'date', 'ticket_price', 'max_tickets', 'poster_image']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            })
    
    def clean_poster_image(self):
        poster_image = self.cleaned_data.get('poster_image')
        if poster_image:
            if hasattr(poster_image, 'size') and poster_image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large (must be under 5MB).")
        return poster_image
