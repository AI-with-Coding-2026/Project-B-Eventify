from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser

INPUT_CLASSES = (
    'w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 '
    'placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none '
    'focus:ring-2 focus:ring-indigo-500/20 transition-colors'
)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})
