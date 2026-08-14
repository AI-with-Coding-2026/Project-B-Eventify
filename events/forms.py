from django import forms

from .models import Category, Event


class EventForm(forms.ModelForm):
    """Organizer event create/edit form. Ownership is set in the view."""

    class Meta:
        model = Event
        fields = ['title', 'description', 'image', 'date', 'price', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your event',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if (
            image
            and hasattr(image, 'content_type')
            and image.content_type
            not in [
                'image/jpeg',
                'image/png',
                'image/webp',
            ]
        ):
            raise forms.ValidationError(
                'Only JPG, PNG, and WebP images are allowed.'
            )

        return image


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if not name:
            raise forms.ValidationError(
                'Category name cannot be empty.'
            )

        # Exclude the current category on edit.
        # Without this, saving the same name would fail uniqueness against itself.
        duplicates = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise forms.ValidationError(
                'A category with this name already exists.'
            )

        return name
