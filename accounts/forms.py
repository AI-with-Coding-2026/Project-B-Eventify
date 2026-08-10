from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='First name',
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Last name',
    )

    email = forms.EmailField(
        required=True,
        label='Email address',
    )

    role = forms.ChoiceField(
        choices=[
            (User.Role.ORGANIZER, 'Organizer'),
            (User.Role.ATTENDEE, 'Attendee'),
        ],
        label='Role',
    )

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'password1',
            'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'