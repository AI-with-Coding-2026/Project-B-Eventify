from django import forms

from .models import Category, Event


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

        if Category.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                'A category with this name already exists.'
            )

        return name

class EventForm(forms.ModelForm):

    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Event

        fields = [
            "title",
            "description",
            "location",
            "date",
            "price",
            "max_tickets",
            "image",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "max_tickets": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if (
            image
            and hasattr(image, "content_type")
            and image.content_type
            not in [
                "image/jpeg",
                "image/png",
                "image/webp",
            ]
        ):
            raise forms.ValidationError(
                "Only JPG, PNG, and WebP images are allowed."
            )

        return image