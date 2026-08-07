from django import forms
from django.contrib.auth.admin import UserAdmin

from .admin_site import eventify_admin_site
from .models import User, UserRole


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'role')

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserRole.ADMIN and not self.request_user.is_superuser:
            raise forms.ValidationError('Only superusers can assign the Admin role.')
        return role

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if user.role == UserRole.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == UserRole.ADMIN and not self.request_user.is_superuser:
            raise forms.ValidationError('Only superusers can assign the Admin role.')
        return role


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        defaults = {'form': CustomUserChangeForm if obj else CustomUserCreationForm}
        defaults.update(kwargs)
        form = super().get_form(request, obj, **defaults)

        class RequestAwareForm(form):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)
                self.request_user = request.user

        return RequestAwareForm

    def has_view_permission(self, request, obj=None):
        return request.user.is_admin

    def has_add_permission(self, request):
        return request.user.is_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_admin

    def has_delete_permission(self, request, obj=None):
        return request.user.is_admin

    def save_model(self, request, obj, form, change):
        obj.is_staff = obj.role == UserRole.ADMIN
        super().save_model(request, obj, form, change)


eventify_admin_site.register(User, CustomUserAdmin)
