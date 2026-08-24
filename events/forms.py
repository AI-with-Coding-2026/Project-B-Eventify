from django import forms
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
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Enter category name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 3,
                    "placeholder": "Optional description",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Category name cannot be empty."
            )

        duplicates = Category.objects.filter(name__iexact=name)

        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise forms.ValidationError(
                "A category with this name already exists."
            )

        return name


class EventForm(forms.ModelForm):
    """
    Form for creating and editing events.

    An event can now have multiple categories through the
    Event.categories Many-to-Many relationship.
    """

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Categories",
        help_text="Select one or more categories for this event.",
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "location",
            "image",
            "date",
            "price",
            "max_tickets",
            "categories",
            "custom_category",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter event title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter event description",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter event location",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
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
            "custom_category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional custom category",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Always load categories from the database.
        self.fields["categories"].queryset = Category.objects.all()

        # When editing an existing Event, Django automatically
        # loads the currently selected Many-to-Many categories.

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image:
            # Keep any existing image validation here if required.
            pass

        return image


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["event", "attendee", "quantity"]
        widgets = {
            "event": forms.Select(
                attrs={"class": INPUT_CLASSES}
            ),
            "attendee": forms.Select(
                attrs={"class": INPUT_CLASSES}
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "min": 1,
                }
            ),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = EventBooking
        fields = ["user", "event"]
        widgets = {
            "user": forms.Select(
                attrs={"class": INPUT_CLASSES}
            ),
            "event": forms.Select(
                attrs={"class": INPUT_CLASSES}
            ),
        }