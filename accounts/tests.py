from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email="attendee@example.com",
            password="StrongTestPassword123!",
            first_name="Test",
            last_name="Attendee",
            role=User.Role.ATTENDEE,
        )

        self.assertEqual(user.email, "attendee@example.com")
        self.assertEqual(user.role, User.Role.ATTENDEE)
        self.assertTrue(user.check_password("StrongTestPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_not_stored_as_plain_text(self):
        raw_password = "StrongTestPassword123!"

        user = User.objects.create_user(
            email="secure@example.com",
            password=raw_password,
        )

        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.check_password(raw_password))

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongAdminPassword123!",
        )

        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


class RegistrationTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/register.html",
        )

    def test_attendee_can_register(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "John",
                "last_name": "Smith",
                "email": "john@example.com",
                "role": User.Role.ATTENDEE,
                "password1": "StrongTestPassword123!",
                "password2": "StrongTestPassword123!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(
            User.objects.filter(email="john@example.com").exists()
        )

    def test_public_user_cannot_register_as_admin(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Fake",
                "last_name": "Admin",
                "email": "fake-admin@example.com",
                "role": User.Role.ADMIN,
                "password1": "StrongTestPassword123!",
                "password2": "StrongTestPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                email="fake-admin@example.com"
            ).exists()
        )

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="existing@example.com",
            password="StrongTestPassword123!",
        )

        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Another",
                "last_name": "User",
                "email": "existing@example.com",
                "role": User.Role.ATTENDEE,
                "password1": "AnotherStrongPassword123!",
                "password2": "AnotherStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            User.objects.filter(
                email="existing@example.com"
            ).count(),
            1,
        )


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "StrongTestPassword123!"

        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            first_name="Example",
            last_name="User",
            role=User.Role.ORGANIZER,
        )

    def test_user_can_log_in(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.user.email,
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))

    def test_invalid_password_does_not_log_user_in(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.user.email,
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)

        dashboard_response = self.client.get(
            reverse("dashboard")
        )

        expected_url = (
            f"{reverse('login')}?next={reverse('dashboard')}"
        )

        self.assertRedirects(
            dashboard_response,
            expected_url,
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))

        expected_url = (
            f"{reverse('login')}?next={reverse('dashboard')}"
        )

        self.assertRedirects(response, expected_url)

    def test_authenticated_user_can_access_dashboard(self):
        self.client.login(
            email=self.user.email,
            password=self.password,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/dashboard.html",
        )

    def test_user_can_log_out(self):
        self.client.login(
            email=self.user.email,
            password=self.password,
        )

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))

        dashboard_response = self.client.get(
            reverse("dashboard")
        )

        expected_url = (
            f"{reverse('login')}?next={reverse('dashboard')}"
        )

        self.assertRedirects(
            dashboard_response,
            expected_url,
        )
