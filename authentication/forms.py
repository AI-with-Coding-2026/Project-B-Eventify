from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, UserRole


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[
            (UserRole.ORGANIZER, UserRole.ORGANIZER.label),
            (UserRole.ATTENDEE, UserRole.ATTENDEE.label),
        ],
        initial=UserRole.ATTENDEE,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserRole.ADMIN:
            raise forms.ValidationError('Admin accounts cannot be created through registration.')
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user
