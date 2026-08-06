from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .forms import UserRegistrationForm
from .models import User, UserRole


class UserRoleModelTests(TestCase):
    def test_create_user_defaults_to_attendee(self):
        user = User.objects.create_user('attendee1', 'attendee1@example.com', 'pass123')
        self.assertEqual(user.role, UserRole.ATTENDEE)
        self.assertTrue(user.is_attendee)

    def test_create_user_as_organizer(self):
        user = User.objects.create_user(
            'organizer1',
            'organizer1@example.com',
            'pass123',
            role=UserRole.ORGANIZER,
        )
        self.assertEqual(user.role, UserRole.ORGANIZER)
        self.assertTrue(user.is_organizer)

    def test_create_superuser_gets_admin_role(self):
        user = User.objects.create_superuser('admin1', 'admin1@example.com', 'pass123')
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_admin_role_requires_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                'badadmin',
                'badadmin@example.com',
                'pass123',
                role=UserRole.ADMIN,
            )

    def test_superuser_must_keep_admin_role(self):
        user = User.objects.create_superuser('admin2', 'admin2@example.com', 'pass123')
        user.role = UserRole.ORGANIZER
        with self.assertRaises(ValidationError):
            user.save()


class UserRegistrationFormTests(TestCase):
    def test_registration_form_accepts_organizer(self):
        form = UserRegistrationForm(
            data={
                'username': 'orguser',
                'email': 'orguser@example.com',
                'role': UserRole.ORGANIZER,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, UserRole.ORGANIZER)

    def test_registration_form_accepts_attendee(self):
        form = UserRegistrationForm(
            data={
                'username': 'attuser',
                'email': 'attuser@example.com',
                'role': UserRole.ATTENDEE,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, UserRole.ATTENDEE)

    def test_registration_form_rejects_admin_role(self):
        form = UserRegistrationForm(
            data={
                'username': 'hackadmin',
                'email': 'hackadmin@example.com',
                'role': UserRole.ADMIN,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('role', form.errors)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_view_creates_user_with_selected_role(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'vieworg',
                'email': 'vieworg@example.com',
                'role': UserRole.ORGANIZER,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            },
        )
        self.assertRedirects(response, reverse('register_success'))
        user = User.objects.get(username='vieworg')
        self.assertEqual(user.role, UserRole.ORGANIZER)
