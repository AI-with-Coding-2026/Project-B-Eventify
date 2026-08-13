from django.test import Client, TestCase
from django.urls import reverse
from django.contrib import admin

from authentication.models import User, UserRole

from django.utils import timezone

from .models import Category, Event, Ticket


# Tests for admin category update/edit
class CategoryUpdateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            'categoryadmin',
            'categoryadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'categoryorganizer',
            'categoryorganizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.category = Category.objects.create(
            name='Music',
            description='Live shows and concerts',
        )

    def test_admin_can_load_edit_form(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('category_update', kwargs={'pk': self.category.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Category')
        self.assertContains(response, self.category.name)

    def test_admin_can_update_category_name(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('category_update', kwargs={'pk': self.category.pk}),
            {
                'name': 'Live Music',
                'description': 'Updated description',
            },
        )

        self.assertRedirects(
            response,
            reverse('category_update', kwargs={'pk': self.category.pk}),
        )
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Live Music')
        self.assertEqual(self.category.description, 'Updated description')

    def test_admin_can_keep_same_category_name(self):
        # Ensures the form fix allows keeping the existing name
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('category_update', kwargs={'pk': self.category.pk}),
            {
                'name': 'Music',
                'description': 'Slightly updated description',
            },
        )

        self.assertRedirects(
            response,
            reverse('category_update', kwargs={'pk': self.category.pk}),
        )
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Music')
        self.assertEqual(
            self.category.description,
            'Slightly updated description',
        )

    def test_update_rejects_duplicate_category_name(self):
        Category.objects.create(name='Sports')
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('category_update', kwargs={'pk': self.category.pk}),
            {
                'name': 'Sports',
                'description': 'Should fail',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A category with this name already exists.')
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Music')

    def test_non_admin_cannot_update_category(self):
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse('category_update', kwargs={'pk': self.category.pk})
        )

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )


class OrganizerEventPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer_a = User.objects.create_user(
            'organizer_a',
            'organizer_a@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.organizer_b = User.objects.create_user(
            'organizer_b',
            'organizer_b@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'attendee_user',
            'attendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.event_a = Event.objects.create(
            organizer=self.organizer_a,
            title='Organizer A Event',
            description='Owned by A',
            date=timezone.now(),
            price='10.00',
            category='music',
        )

    def test_organizer_sees_only_own_events(self):
        Event.objects.create(
            organizer=self.organizer_b,
            title='Organizer B Event',
            description='Owned by B',
            date=timezone.now(),
            price='20.00',
            category='tech',
        )
        self.client.force_login(self.organizer_a)

        response = self.client.get(reverse('organizer_event_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organizer A Event')
        self.assertNotContains(response, 'Organizer B Event')

    def test_organizer_can_create_event_owned_by_self(self):
        self.client.force_login(self.organizer_a)

        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'New Concert',
                'description': 'Live night',
                'date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'price': '15.00',
                'category': 'music',
            },
        )

        self.assertRedirects(response, reverse('organizer_event_list'))
        event = Event.objects.get(title='New Concert')
        self.assertEqual(event.organizer, self.organizer_a)

    def test_organizer_cannot_edit_another_organizer_event(self):
        self.client.force_login(self.organizer_b)

        response = self.client.get(
            reverse('event_edit', kwargs={'pk': self.event_a.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_organizer_cannot_delete_another_organizer_event(self):
        self.client.force_login(self.organizer_b)

        response = self.client.post(
            reverse('event_delete', kwargs={'pk': self.event_a.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Event.objects.filter(pk=self.event_a.pk).exists())

    def test_attendee_cannot_access_organizer_event_pages(self):
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('organizer_event_list'))

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )


class AttendeeTicketBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            'ticket_organizer',
            'ticket_organizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'ticket_attendee',
            'ticket_attendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Bookable Show',
            description='Open for booking',
            date=timezone.now(),
            price='25.00',
            category='arts',
        )

    def test_attendee_can_browse_events(self):
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('event_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bookable Show')
        self.assertContains(response, 'Book ticket')

    def test_attendee_can_book_ticket(self):
        self.client.force_login(self.attendee)

        response = self.client.post(
            reverse('book_ticket', kwargs={'pk': self.event.pk}),
            {'quantity': 2},
        )

        self.assertRedirects(response, reverse('my_tickets'))
        ticket = Ticket.objects.get(
            event=self.event,
            attendee=self.attendee,
        )
        self.assertEqual(ticket.quantity, 2)

    def test_attendee_can_view_own_tickets(self):
        Ticket.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=1,
        )
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('my_tickets'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bookable Show')

    def test_organizer_cannot_book_ticket(self):
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse('book_ticket', kwargs={'pk': self.event.pk})
        )

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )


class CategoryDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            'deleteadmin',
            'deleteadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'deleteorganizer',
            'deleteorganizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'deleteattendee',
            'deleteattendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.category = Category.objects.create(
            name='To Be Deleted',
            description='This category will be deleted',
        )
        self.delete_url = reverse(
            'category_delete',
            kwargs={'pk': self.category.pk},
        )

    def test_admin_can_access_delete_confirmation(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Category')
        self.assertContains(response, self.category.name)

    def test_admin_can_delete_category(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.delete_url)

        self.assertRedirects(response, reverse('category_list'))
        self.assertFalse(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_non_admin_organizer_cannot_delete_category(self):
        self.client.force_login(self.organizer)

        response = self.client.post(self.delete_url)

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )
        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_non_admin_attendee_cannot_delete_category(self):
        self.client.force_login(self.attendee)

        response = self.client.post(self.delete_url)

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )
        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_unauthenticated_user_cannot_delete_category(self):
        response = self.client.post(self.delete_url)

        self.assertRedirects(
            response,
            reverse('eventify_admin:login') + '?next=' + self.delete_url,
        )
        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_deleting_nonexistent_category_returns_404(self):
        self.client.force_login(self.admin)

        invalid_url = reverse(
            'category_delete',
            kwargs={'pk': 9999},
        )
        response = self.client.post(invalid_url)

        self.assertEqual(response.status_code, 404)

    def test_get_confirmation_does_not_delete_category(self):
        """Opening the confirmation page via GET must NOT delete the category."""
        self.client.force_login(self.admin)

        self.client.get(self.delete_url)

        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_successful_deletion_shows_success_message(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.delete_url, follow=True)

        self.assertContains(response, 'Category deleted successfully.')

    def test_cancel_leaves_category_unchanged(self):
        """Visiting the confirmation page and navigating away (cancel)
        must leave the category in the database."""
        self.client.force_login(self.admin)

        # Simulate cancel: GET the confirmation page, then navigate to the list
        self.client.get(self.delete_url)
        self.client.get(reverse('category_list'))

        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )

class CategoryListTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            'listadmin',
            'listadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'listorganizer',
            'listorganizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'listattendee',
            'listattendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )

        self.cat1 = Category.objects.create(name='Cat 1', description='First category')
        self.cat2 = Category.objects.create(name='Cat 2')

    def test_admin_can_view_category_list(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('category_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cat 1')
        self.assertContains(response, 'Cat 2')

    def test_category_list_displays_description(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('category_list'))

        self.assertContains(response, 'First category')

    def test_category_list_contains_edit_links(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('category_list'))

        edit_url_1 = reverse('category_update', kwargs={'pk': self.cat1.pk})
        edit_url_2 = reverse('category_update', kwargs={'pk': self.cat2.pk})
        self.assertContains(response, edit_url_1)
        self.assertContains(response, edit_url_2)

    def test_category_list_contains_delete_links(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('category_list'))

        delete_url_1 = reverse('category_delete', kwargs={'pk': self.cat1.pk})
        delete_url_2 = reverse('category_delete', kwargs={'pk': self.cat2.pk})
        self.assertContains(response, delete_url_1)
        self.assertContains(response, delete_url_2)

    def test_organizer_cannot_access_category_list(self):
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('category_list'))

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )

    def test_attendee_cannot_access_category_list(self):
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('category_list'))

        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )


class EventAdminDeleteActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            'actionadmin',
            'actionadmin@example.com',
            'strong-pass-123',
        )
        self.organizer = User.objects.create_user(
            'actionorg',
            'actionorg@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            'actionatt',
            'actionatt@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.event1 = Event.objects.create(
            organizer=self.organizer,
            title='Delete Me 1',
            date=timezone.now(),
            price='10.00',
            category='music',
        )
        self.event2 = Event.objects.create(
            organizer=self.organizer,
            title='Delete Me 2',
            date=timezone.now(),
            price='20.00',
            category='tech',
        )
        # Using the custom admin site for events
        self.changelist_url = reverse('eventify_admin:events_event_changelist')

    def test_admin_can_see_delete_action_confirmation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.changelist_url,
            {
                'action': 'delete_selected_events',
                admin.helpers.ACTION_CHECKBOX_NAME: [self.event1.pk],
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Are you sure you want to delete this event?')
        self.assertContains(response, self.event1.title)

    def test_admin_can_confirm_delete(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.changelist_url,
            {
                'action': 'delete_selected_events',
                admin.helpers.ACTION_CHECKBOX_NAME: [self.event1.pk],
                'post': 'yes',
            },
            follow=True
        )
        self.assertFalse(Event.objects.filter(pk=self.event1.pk).exists())
        self.assertContains(response, 'Event deleted successfully.')

    def test_admin_can_confirm_multiple_delete(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.changelist_url,
            {
                'action': 'delete_selected_events',
                admin.helpers.ACTION_CHECKBOX_NAME: [self.event1.pk, self.event2.pk],
                'post': 'yes',
            },
            follow=True
        )
        self.assertFalse(Event.objects.filter(pk=self.event1.pk).exists())
        self.assertFalse(Event.objects.filter(pk=self.event2.pk).exists())
        self.assertContains(response, 'Events deleted successfully.')

    def test_organizer_cannot_access_eventify_admin_changelist(self):
        self.client.force_login(self.organizer)
        response = self.client.get(self.changelist_url)
        # Organizer gets 403 redirected to /unauthorized/
        self.assertRedirects(response, reverse('unauthorized'), target_status_code=403)

    def test_attendee_cannot_access_eventify_admin_changelist(self):
        self.client.force_login(self.attendee)
        response = self.client.get(self.changelist_url)
        self.assertRedirects(response, reverse('unauthorized'), target_status_code=403)

    def test_unauthenticated_cannot_access_eventify_admin_changelist(self):
        response = self.client.get(self.changelist_url)
        self.assertRedirects(response, reverse('eventify_admin:login') + '?next=' + self.changelist_url)