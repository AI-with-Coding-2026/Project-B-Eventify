from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm

from .models import OrganizerApprovalStatus, User, UserRole


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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists. Please log in or use a different email."
            )
        return email

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserRole.ADMIN:
            raise forms.ValidationError('Admin accounts cannot be created through registration.')
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if user.role == UserRole.ORGANIZER:
            user.organizer_status = OrganizerApprovalStatus.PENDING
        else:
            user.organizer_status = OrganizerApprovalStatus.NOT_REQUIRED
        if commit:
            user.save()
        return user


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email',
        }),
    )
