from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from unittest.mock import ANY, patch

from .forms import UserRegistrationForm
from .models import User, UserRole
from . import views


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


class RoleBasedAccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            'admin_rbac',
            'admin_rbac@example.com',
            'pass123',
        )
        self.organizer = User.objects.create_user(
            'organizer_rbac',
            'organizer_rbac@example.com',
            'pass123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'attendee_rbac',
            'attendee_rbac@example.com',
            'pass123',
            role=UserRole.ATTENDEE,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('organizer_dashboard')}")

    def test_organizer_can_access_organizer_dashboard(self):
        self.client.login(username='organizer_rbac', password='pass123')
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_attendee_cannot_access_organizer_dashboard(self):
        self.client.login(username='attendee_rbac', password='pass123')
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_attendee_can_access_attendee_dashboard(self):
        self.client.login(username='attendee_rbac', password='pass123')
        response = self.client.get(reverse('attendee_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_organizer_cannot_access_attendee_dashboard(self):
        self.client.login(username='organizer_rbac', password='pass123')
        response = self.client.get(reverse('attendee_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_organizer_dashboard(self):
        self.client.login(username='admin_rbac', password='pass123')
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_attendee_dashboard(self):
        self.client.login(username='admin_rbac', password='pass123')
        response = self.client.get(reverse('attendee_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_login_redirects_organizer_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'organizer_rbac', 'password': 'pass123'},
        )
        self.assertRedirects(response, reverse('organizer_dashboard'))

    def test_login_redirects_attendee_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'attendee_rbac', 'password': 'pass123'},
        )
        self.assertRedirects(response, reverse('attendee_dashboard'))


class AdminAccessTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            'adminuser',
            'adminuser@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'organizeruser',
            'organizeruser@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'attendeeuser',
            'attendeeuser@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

    def test_admin_dashboard_is_available_to_admin_role(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_admin_dashboard_denies_organizer_with_unauthorized(self):
        """Organizer accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('admin_dashboard'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_admin_dashboard_denies_attendee_with_unauthorized(self):
        """Attendee accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('admin_dashboard'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_custom_admin_site_is_mounted_and_restricted_to_admin_role(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('eventify_admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Eventify Administration')

    def test_admin_role_can_view_users_in_custom_admin_site(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('eventify_admin:authentication_user_changelist')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.organizer.username)

    def test_custom_admin_site_denies_organizer_with_unauthorized(self):
        """Organizer accessing /django-admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('eventify_admin:index'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_custom_admin_site_denies_attendee_with_unauthorized(self):
        """Attendee accessing /django-admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('eventify_admin:index'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')


class RoleDashboardAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            'dashboardadmin',
            'dashboardadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'dashboardorganizer',
            'dashboardorganizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'dashboardattendee',
            'dashboardattendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

    def test_admin_can_access_organizer_and_attendee_dashboards(self):
        request = self.factory.get('/dashboard/organizer/')
        request.user = self.admin
        with patch('authentication.views.render', return_value=HttpResponse()) as render:
            self.assertEqual(views.organizer_dashboard(request).status_code, 200)
            render.assert_called_once_with(
                request,
                'authentication/organizer_dashboard.html',
                {'upcoming_events': ANY},
            )

        request = self.factory.get('/dashboard/attendee/')
        request.user = self.admin
        with patch('authentication.views.render', return_value=HttpResponse()) as render:
            self.assertEqual(views.attendee_dashboard(request).status_code, 200)
            render.assert_called_once_with(
                request,
                'authentication/attendee_dashboard.html',
                {'upcoming_events': ANY},
            )

    def test_organizer_and_attendee_remain_isolated(self):
        request = self.factory.get('/dashboard/attendee/')
        request.user = self.organizer
        with self.assertRaises(PermissionDenied):
            views.attendee_dashboard(request)

        request = self.factory.get('/dashboard/organizer/')
        request.user = self.attendee
        with self.assertRaises(PermissionDenied):
            views.organizer_dashboard(request)
