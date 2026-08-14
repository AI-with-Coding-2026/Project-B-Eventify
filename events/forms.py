from django import forms

from .models import Category, Event

INPUT_CLASSES = (
    "mt-1 block w-full rounded-xl border border-[#dbeeff] bg-white px-3 py-2.5 "
    "text-sm text-gray-900 shadow-sm transition placeholder:text-gray-400 "
    "focus:border-[#2c7be5] focus:outline-none focus:ring-4 focus:ring-[#dbeeff]"
)

TEXTAREA_CLASSES = INPUT_CLASSES + " min-h-[120px]"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Enter category name',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
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

        duplicates = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise forms.ValidationError(
                'A category with this name already exists.'
            )

        return name


class EventForm(forms.ModelForm):

    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": INPUT_CLASSES,
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
            "category",
            "image",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": INPUT_CLASSES}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 5,
                }
            ),
            "location": forms.TextInput(
                attrs={"class": INPUT_CLASSES}
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "max_tickets": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "min": "1",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": INPUT_CLASSES,
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASSES,
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