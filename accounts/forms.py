from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First name",
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last name",
    )

    email = forms.EmailField(
        required=True,
        label="Email address",
    )

    role = forms.ChoiceField(
        choices=[
            (User.Role.ORGANIZER, "Organizer"),
            (User.Role.ATTENDEE, "Attendee"),
        ],
        label="Account role",
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
            }
        ),
    )