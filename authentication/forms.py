from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User, UserRole


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
            (UserRole.ORGANIZER, UserRole.ORGANIZER.label),
            (UserRole.ATTENDEE, UserRole.ATTENDEE.label),
        ],
        initial=UserRole.ATTENDEE,
        label='Account role',
    )

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'username',
            'email',
            'role',
            'password1',
            'password2',
        )

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserRole.ADMIN:
            raise forms.ValidationError(
                'Admin accounts cannot be created through registration.'
            )
        return role

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user
