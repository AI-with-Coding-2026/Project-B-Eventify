from django.core.exceptions import ValidationError
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

    def test_full_name_property_returns_name_when_available(self):
        user = User.objects.create_user(
            'testuser',
            'testuser@example.com',
            'pass123',
            first_name='John',
            last_name='Doe',
        )
        self.assertEqual(user.full_name, 'John Doe')

    def test_full_name_property_falls_back_to_username(self):
        user = User.objects.create_user(
            'testuser',
            'testuser@example.com',
            'pass123',
        )
        self.assertEqual(user.full_name, 'testuser')


class UserRegistrationFormTests(TestCase):
    def test_registration_form_accepts_organizer(self):
        form = UserRegistrationForm(
            data={
                'first_name': 'Org',
                'last_name': 'User',
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
        self.assertEqual(user.first_name, 'Org')
        self.assertEqual(user.last_name, 'User')

    def test_registration_form_accepts_attendee(self):
        form = UserRegistrationForm(
            data={
                'first_name': 'Att',
                'last_name': 'User',
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
                'first_name': 'Hack',
                'last_name': 'Admin',
                'username': 'hackadmin',
                'email': 'hackadmin@example.com',
                'role': UserRole.ADMIN,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('role', form.errors)

    def test_registration_form_rejects_duplicate_email(self):
        User.objects.create_user(
            'existing',
            'taken@example.com',
            'pass123',
        )
        form = UserRegistrationForm(
            data={
                'first_name': 'New',
                'last_name': 'User',
                'username': 'newuser',
                'email': 'taken@example.com',
                'role': UserRole.ATTENDEE,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_registration_form_requires_first_and_last_name(self):
        form = UserRegistrationForm(
            data={
                'username': 'noname',
                'email': 'noname@example.com',
                'role': UserRole.ATTENDEE,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_view_creates_user_and_auto_logs_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'View',
                'last_name': 'Org',
                'username': 'vieworg',
                'email': 'vieworg@example.com',
                'role': UserRole.ORGANIZER,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            },
        )
        # Should redirect to the organizer dashboard after auto-login.
        self.assertRedirects(response, reverse('organizer_dashboard'))

        # User should exist in the database.
        user = User.objects.get(username='vieworg')
        self.assertEqual(user.role, UserRole.ORGANIZER)
        self.assertEqual(user.first_name, 'View')
        self.assertEqual(user.last_name, 'Org')

        # User should be logged in.
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_register_view_saves_first_and_last_name(self):
        self.client.post(
            reverse('register'),
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'username': 'janesmith',
                'email': 'jane@example.com',
                'role': UserRole.ATTENDEE,
                'password1': 'strong-pass-123',
                'password2': 'strong-pass-123',
            },
        )
        user = User.objects.get(username='janesmith')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Smith')


class LoginLogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'loginuser',
            'loginuser@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

    def test_login_with_valid_credentials_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'loginuser',
                'password': 'strong-pass-123',
            },
        )
        self.assertRedirects(response, reverse('attendee_dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_credentials_stays_on_login(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'loginuser',
                'password': 'wrong-password',
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_authenticated_user_visiting_login_redirects_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('login'))
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

    def test_admin_dashboard_is_available_to_admin_role(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_redirects_non_admin_users_to_admin_login(self):
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('admin_dashboard'))

        login_url = reverse('eventify_admin:login')
        self.assertRedirects(
            response,
            f'{login_url}?next={reverse("admin_dashboard")}',
        )

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
                ANY,
            )

        request = self.factory.get('/dashboard/attendee/')
        request.user = self.admin
        with patch('authentication.views.render', return_value=HttpResponse()) as render:
            self.assertEqual(views.attendee_dashboard(request).status_code, 200)
            render.assert_called_once_with(
                request,
                'authentication/attendee_dashboard.html',
                ANY,
            )

    def test_organizer_and_attendee_remain_isolated(self):
        request = self.factory.get('/dashboard/attendee/')
        request.user = self.organizer
        with patch('authentication.decorators.redirect') as redirect:
            views.attendee_dashboard(request)
            redirect.assert_called_once_with('unauthorized')

        request = self.factory.get('/dashboard/organizer/')
        request.user = self.attendee
        with patch('authentication.decorators.redirect') as redirect:
            views.organizer_dashboard(request)
            redirect.assert_called_once_with('unauthorized')


class SessionPersistenceTests(TestCase):
    """Verify that login creates a persistent session across requests."""

    def test_session_persists_across_pages(self):
        user = User.objects.create_user(
            'sessionuser',
            'sessionuser@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

        # Log in
        self.client.post(
            reverse('login'),
            {
                'username': 'sessionuser',
                'password': 'strong-pass-123',
            },
        )

        # Visit multiple pages — user should stay authenticated.
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.get(reverse('attendee_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class StudentManagementTests(TestCase):
    """Tests for admin-only student list, detail, edit, and delete views."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            'studentadmin',
            'studentadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'studentorg',
            'studentorg@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'studentatt',
            'studentatt@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

    # --- Student List ---

    def test_admin_can_view_student_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'studentadmin')
        self.assertContains(response, 'studentorg')
        self.assertContains(response, 'studentatt')

    def test_student_list_search_by_username(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('student_list'), {'q': 'studentorg'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'studentorg')
        self.assertNotContains(response, 'studentatt')

    def test_student_list_filter_by_role(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('student_list'), {'role': 'attendee'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'studentatt')
        self.assertNotContains(response, 'studentorg')

    # --- Student Detail ---

    def test_admin_can_view_student_detail(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('student_detail', kwargs={'pk': self.attendee.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'studentatt')

    def test_student_detail_returns_404_for_nonexistent_user(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('student_detail', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    # --- Student Edit ---

    def test_admin_can_edit_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('student_edit', kwargs={'pk': self.attendee.pk}),
            {
                'first_name': 'Updated',
                'last_name': 'Name',
                'email': 'updated@example.com',
                'role': UserRole.ATTENDEE,
            },
        )
        self.assertRedirects(response, reverse('student_list'))
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.first_name, 'Updated')
        self.assertEqual(self.attendee.last_name, 'Name')
        self.assertEqual(self.attendee.email, 'updated@example.com')

    def test_student_edit_rejects_duplicate_email(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('student_edit', kwargs={'pk': self.attendee.pk}),
            {
                'first_name': 'Att',
                'last_name': 'User',
                'email': 'studentorg@example.com',  # Duplicate
                'role': UserRole.ATTENDEE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    # --- Student Delete ---

    def test_admin_can_delete_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('student_delete', kwargs={'pk': self.attendee.pk})
        )
        self.assertRedirects(response, reverse('student_list'))
        self.assertFalse(User.objects.filter(pk=self.attendee.pk).exists())

    def test_admin_cannot_delete_self(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('student_delete', kwargs={'pk': self.admin.pk})
        )
        self.assertRedirects(response, reverse('student_list'))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_admin_cannot_delete_superuser(self):
        superuser = User.objects.create_superuser(
            'superadmin', 'superadmin@example.com', 'strong-pass-123'
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('student_delete', kwargs={'pk': superuser.pk})
        )
        self.assertRedirects(response, reverse('student_list'))
        self.assertTrue(User.objects.filter(pk=superuser.pk).exists())

    def test_delete_confirmation_page_renders(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('student_delete', kwargs={'pk': self.organizer.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Delete')
        self.assertContains(response, self.organizer.username)

    # --- Non-admin Access Denied ---

    def test_organizer_cannot_access_student_list(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('student_list'))
        # admin_required redirects to admin login
        self.assertNotEqual(response.status_code, 200)

    def test_attendee_cannot_access_student_edit(self):
        self.client.force_login(self.attendee)
        response = self.client.get(
            reverse('student_edit', kwargs={'pk': self.organizer.pk})
        )
        self.assertNotEqual(response.status_code, 200)

    def test_attendee_cannot_access_student_delete(self):
        self.client.force_login(self.attendee)
        response = self.client.post(
            reverse('student_delete', kwargs={'pk': self.organizer.pk})
        )
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.organizer.pk).exists())

