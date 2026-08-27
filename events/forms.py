from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Category, Event, EventBooking, Ticket


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
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Categories",
        help_text="Select one or more categories for this event, or specify a custom category under 'Other'.",
    )

    max_tickets = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASSES,
                "min": "1",
            }
        ),
    )

    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": INPUT_CLASSES,
                "id": "id_date",
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
            "categories",
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
            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        categories = cleaned_data.get("categories")
        custom_category = self.data.get("custom_category", "").strip()

        if not categories and not custom_category:
            self.add_error(
                "categories",
                "Please select at least one category or specify a custom category under 'Other'."
            )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        custom_cat_name = self.data.get("custom_category", "").strip()[:15]
        if custom_cat_name:
            new_cat, _ = Category.objects.get_or_create(name=custom_cat_name)
            if commit:
                instance.categories.add(new_cat)
            else:
                old_save_m2m = getattr(self, "save_m2m", None)

                def new_save_m2m():
                    if old_save_m2m:
                        old_save_m2m()
                    instance.categories.add(new_cat)

                self.save_m2m = new_save_m2m
        return instance

    def clean_max_tickets(self):
        value = self.cleaned_data.get("max_tickets")
        return value or 1

    def clean_date(self):
        date = self.cleaned_data.get("date")
        if date:
            now = timezone.now()
            if not self.instance.pk or (self.instance.pk and self.instance.date != date):
                if date < now:
                    raise forms.ValidationError("Event date and time cannot be in the past.")
                if date > now + timedelta(days=183):
                    raise forms.ValidationError("Event date cannot be more than 6 months in the future.")
        return date

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


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['event', 'attendee', 'quantity']
        widgets = {
            'event': forms.Select(attrs={'class': INPUT_CLASSES}),
            'attendee': forms.Select(attrs={'class': INPUT_CLASSES}),
            'quantity': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 1}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = EventBooking
        fields = ['user', 'event']
        widgets = {
            'user': forms.Select(attrs={'class': INPUT_CLASSES}),
            'event': forms.Select(attrs={'class': INPUT_CLASSES}),
        }

