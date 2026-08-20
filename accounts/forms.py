from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

ROLE_CHOICES = (
    ("guest", "Guest — browse events and book tickets"),
    ("organizer", "Organizer — create and manage events"),
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, widget=forms.RadioSelect, initial="guest"
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "role":
                field.widget.attrs.setdefault("class", "form-control")