from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import ANY, patch

from events.models import Event, EventBooking

from .forms import UserRegistrationForm
from .models import User, UserRole
from . import views


class UserRoleModelTests(TestCase):
    def test_create_user_defaults_to_attendee(self):
        user = User.objects.create_user(
            'attendee1',
            'attendee1@example.com',
            'pass123',
        )
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
        user = User.objects.create_superuser(
            'admin1',
            'admin1@example.com',
            'pass123',
        )
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
        user = User.objects.create_superuser(
            'admin2',
            'admin2@example.com',
            'pass123',
        )
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

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('organizer_dashboard')}",
        )

    def test_organizer_can_access_organizer_dashboard(self):
        self.client.login(
            username='organizer_rbac',
            password='pass123',
        )

        response = self.client.get(reverse('organizer_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_attendee_cannot_access_organizer_dashboard(self):
        """Attendee → organizer dashboard uses the shared unauthorized page."""
        self.client.login(
            username='attendee_rbac',
            password='pass123',
        )

        response = self.client.get(
            reverse('organizer_dashboard'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_attendee_can_access_attendee_dashboard(self):
        self.client.login(
            username='attendee_rbac',
            password='pass123',
        )

        response = self.client.get(reverse('attendee_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_organizer_cannot_access_attendee_dashboard(self):
        """Organizer → attendee dashboard uses the shared unauthorized page."""
        self.client.login(
            username='organizer_rbac',
            password='pass123',
        )

        response = self.client.get(
            reverse('attendee_dashboard'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_admin_can_access_organizer_dashboard(self):
        self.client.login(
            username='admin_rbac',
            password='pass123',
        )

        response = self.client.get(reverse('organizer_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_attendee_dashboard(self):
        self.client.login(
            username='admin_rbac',
            password='pass123',
        )

        response = self.client.get(reverse('attendee_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_login_redirects_organizer_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'organizer_rbac',
                'password': 'pass123',
            },
        )

        self.assertRedirects(
            response,
            reverse('organizer_dashboard'),
        )

    def test_login_redirects_attendee_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'attendee_rbac',
                'password': 'pass123',
            },
        )

        self.assertRedirects(
            response,
            reverse('attendee_dashboard'),
        )


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

    def test_admin_dashboard_renders_for_admin(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'Events')
        self.assertContains(response, 'Tickets')
        self.assertContains(response, 'Bookings')
        self.assertContains(response, 'Manage Categories')
        self.assertNotContains(response, 'Open Django Admin Panel')

    def test_login_redirects_admin_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'adminuser',
                'password': 'strong-pass-123',
            },
        )

        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_admin_dashboard_denies_organizer_with_unauthorized(self):
        """Organizer accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse('admin_dashboard'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(
            response,
            'authentication/unauthorized.html',
        )

    def test_admin_dashboard_denies_attendee_with_unauthorized(self):
        """Attendee accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.attendee)

        response = self.client.get(
            reverse('admin_dashboard'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(
            response,
            'authentication/unauthorized.html',
        )

    def test_custom_admin_site_index_redirects_to_admin_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('eventify_admin:index'))

        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_admin_role_can_view_users_in_custom_admin_site(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('eventify_admin:authentication_user_changelist')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.organizer.username,
        )

    def test_custom_admin_site_denies_organizer_with_unauthorized(self):
        """Organizer accessing /django-admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse('eventify_admin:index'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(
            response,
            'authentication/unauthorized.html',
        )

    def test_custom_admin_site_denies_attendee_with_unauthorized(self):
        """Attendee accessing /django-admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.attendee)

        response = self.client.get(
            reverse('eventify_admin:index'),
            follow=True,
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(
            response,
            'authentication/unauthorized.html',
        )


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

        with patch(
            'authentication.views.render',
            return_value=HttpResponse(),
        ) as render:
            self.assertEqual(
                views.organizer_dashboard(request).status_code,
                200,
            )

            render.assert_called_once_with(
                request,
                'authentication/organizer_dashboard.html',
                {
                    'event_stats': ANY,
                    'total_tickets_sold': ANY,
                    'total_revenue': ANY,
                },
            )

        request = self.factory.get('/dashboard/attendee/')
        request.user = self.admin

        with patch(
            'authentication.views.render',
            return_value=HttpResponse(),
        ) as render:
            self.assertEqual(
                views.attendee_dashboard(request).status_code,
                200,
            )

            render.assert_called_once_with(
                request,
                'authentication/attendee_dashboard.html',
                {'upcoming_events': ANY},
            )

    def test_organizer_and_attendee_remain_isolated(self):
        request = self.factory.get('/dashboard/attendee/')
        request.user = self.organizer

        response = views.attendee_dashboard(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('unauthorized'))

        request = self.factory.get('/dashboard/organizer/')
        request.user = self.attendee

        response = views.organizer_dashboard(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('unauthorized'))


class OrganizerDashboardSalesTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.organizer = User.objects.create_user(
            'sales_organizer',
            'sales_organizer@example.com',
            'pass123',
            role=UserRole.ORGANIZER,
        )

        self.other_organizer = User.objects.create_user(
            'other_organizer',
            'other_organizer@example.com',
            'pass123',
            role=UserRole.ORGANIZER,
        )

        self.attendee_one = User.objects.create_user(
            'attendee_one',
            'attendee_one@example.com',
            'pass123',
            role=UserRole.ATTENDEE,
        )

        self.attendee_two = User.objects.create_user(
            'attendee_two',
            'attendee_two@example.com',
            'pass123',
            role=UserRole.ATTENDEE,
        )

        self.event_a = Event.objects.create(
            title='Summer Concert',
            organizer=self.organizer,
            date=timezone.now() + timedelta(days=10),
            price=Decimal('50.00'),
            max_tickets=100,
        )

        self.event_b = Event.objects.create(
            title='Tech Meetup',
            organizer=self.organizer,
            date=timezone.now() + timedelta(days=20),
            price=Decimal('25.00'),
            max_tickets=50,
        )

        self.other_event = Event.objects.create(
            title='Other Event',
            organizer=self.other_organizer,
            date=timezone.now() + timedelta(days=5),
            price=Decimal('10.00'),
            max_tickets=20,
        )

        EventBooking.objects.create(user=self.attendee_one, event=self.event_a)
        EventBooking.objects.create(user=self.attendee_two, event=self.event_a)
        EventBooking.objects.create(user=self.attendee_one, event=self.event_b)
        EventBooking.objects.create(user=self.attendee_one, event=self.other_event)

    def test_organizer_sees_only_their_event_sales(self):
        self.client.login(username='sales_organizer', password='pass123')

        response = self.client.get(reverse('organizer_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Summer Concert')
        self.assertContains(response, 'Tech Meetup')
        self.assertNotContains(response, 'Other Event')

    def test_organizer_dashboard_calculates_sales_metrics(self):
        self.client.login(username='sales_organizer', password='pass123')

        response = self.client.get(reverse('organizer_dashboard'))

        self.assertEqual(response.context['total_tickets_sold'], 3)
        self.assertEqual(response.context['total_revenue'], Decimal('125.00'))

        stats_by_title = {
            row['event'].title: row
            for row in response.context['event_stats']
        }

        self.assertEqual(stats_by_title['Summer Concert']['tickets_sold'], 2)
        self.assertEqual(stats_by_title['Summer Concert']['tickets_remaining'], 98)
        self.assertEqual(stats_by_title['Summer Concert']['revenue'], Decimal('100.00'))

        self.assertEqual(stats_by_title['Tech Meetup']['tickets_sold'], 1)
        self.assertEqual(stats_by_title['Tech Meetup']['tickets_remaining'], 49)
        self.assertEqual(stats_by_title['Tech Meetup']['revenue'], Decimal('25.00'))

    def test_organizer_with_no_events_sees_empty_state(self):
        User.objects.create_user(
            'empty_organizer',
            'empty_organizer@example.com',
            'pass123',
            role=UserRole.ORGANIZER,
        )
        self.client.login(username='empty_organizer', password='pass123')

        response = self.client.get(reverse('organizer_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_tickets_sold'], 0)
        self.assertEqual(response.context['total_revenue'], Decimal('0.00'))
        self.assertContains(response, "You haven't created any events yet")
