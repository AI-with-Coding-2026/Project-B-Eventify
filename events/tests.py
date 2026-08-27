from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib import admin
from django.utils import timezone

from authentication.models import User, UserRole

from .emails import send_booking_confirmation_email
from .models import Category, Event, EventBooking, Ticket


# Tests for admin category creation
class CategoryCreateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            'createadmin',
            'createadmin@example.com',
            'strong-pass-123',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.organizer = User.objects.create_user(
            'createorganizer',
            'createorganizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )

    def test_admin_can_load_create_form(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('category_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Category')
        self.assertContains(response, reverse('admin_dashboard'))

    def test_admin_can_create_category_and_redirects_to_admin_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('category_create'),
            {
                'name': 'Art & Design',
                'description': 'Creative arts and exhibitions',
            },
        )
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertTrue(Category.objects.filter(name='Art & Design').exists())

    def test_create_category_shows_success_message(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('category_create'),
            {
                'name': 'Workshops',
                'description': 'Hands-on learning sessions',
            },
            follow=True,
        )
        self.assertContains(response, 'Category created successfully.')

    def test_non_admin_cannot_access_category_create(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('category_create'))
        self.assertRedirects(
            response,
            reverse('unauthorized'),
            target_status_code=403,
        )


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
        self.music_category = Category.objects.create(
            name='Music',
            slug='music',
        )
        self.tech_category = Category.objects.create(
            name='Tech',
            slug='tech',
        )
        self.event_a = Event.objects.create(
            organizer=self.organizer_a,
            title='Organizer A Event',
            description='Owned by A',
            date=timezone.now() + timedelta(days=2),
            price='10.00',
        )
        self.event_a.categories.add(self.music_category)

    def test_organizer_sees_only_own_events(self):
        event_b = Event.objects.create(
            organizer=self.organizer_b,
            title='Organizer B Event',
            description='Owned by B',
            date=timezone.now() + timedelta(days=2),
            price='20.00',
        )
        event_b.categories.add(self.tech_category)
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
                'date': (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
                'price': '15.00',
                'categories': [self.music_category.pk],
            },
        )

        self.assertRedirects(response, reverse('my_events'))
        event = Event.objects.get(title='New Concert')
        self.assertEqual(event.organizer, self.organizer_a)
        self.assertIn(self.music_category, event.categories.all())

    def test_organizer_can_select_multiple_categories(self):
        self.client.force_login(self.organizer_a)

        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'Tech Music Night',
                'description': 'Music and Tech',
                'date': (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
                'price': '20.00',
                'categories': [self.music_category.pk, self.tech_category.pk],
            },
        )

        self.assertRedirects(response, reverse('my_events'))
        event = Event.objects.get(title='Tech Music Night')
        self.assertEqual(event.categories.count(), 2)
        self.assertIn(self.music_category, event.categories.all())
        self.assertIn(self.tech_category, event.categories.all())

    def test_cannot_create_event_with_past_date(self):
        self.client.force_login(self.organizer_a)

        past_date = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'Past Event',
                'description': 'Event in past',
                'date': past_date,
                'price': '10.00',
                'categories': [self.music_category.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Event date and time cannot be in the past.')
        self.assertFalse(Event.objects.filter(title='Past Event').exists())

    def test_cannot_create_event_more_than_six_months_ahead(self):
        self.client.force_login(self.organizer_a)

        far_future_date = (timezone.now() + timedelta(days=200)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'Far Future Event',
                'description': 'Event in far future',
                'date': far_future_date,
                'price': '10.00',
                'categories': [self.music_category.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Event date cannot be more than 6 months in the future.')
        self.assertFalse(Event.objects.filter(title='Far Future Event').exists())

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
        self.other_attendee = User.objects.create_user(
            'second_ticket_attendee',
            'second_ticket_attendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.arts_category = Category.objects.create(
            name='Arts',
            slug='arts',
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Bookable Show',
            description='Open for booking',
            date=timezone.now() + timedelta(days=1),
            price='25.00',
            max_tickets=3,
        )
        self.event.categories.add(self.arts_category)

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

        self.assertRedirects(response, reverse('my_bookings'))
        ticket = Ticket.objects.get(
            event=self.event,
            attendee=self.attendee,
        )
        self.assertEqual(ticket.quantity, 2)

    def test_booking_page_shows_event_image_and_full_total(self):
        self.event.image = SimpleUploadedFile(
            'show.png',
            (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
                b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05'
                b'\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            ),
            content_type='image/png',
        )
        self.event.save()
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('book_ticket', kwargs={'pk': self.event.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.image.url)
        self.assertContains(response, 'alt="Bookable Show"')
        self.assertContains(response, 'Total:')
        self.assertContains(response, 'id="booking-total"')
        self.assertContains(response, 'data-unit-price="25.00"')

    def test_card_and_detail_use_the_same_ticket_page(self):
        self.client.force_login(self.attendee)
        ticket_url = reverse('book_ticket', kwargs={'pk': self.event.pk})

        list_response = self.client.get(reverse('event_list'))
        detail_response = self.client.get(
            reverse('event_detail', kwargs={'pk': self.event.pk})
        )

        self.assertContains(list_response, ticket_url)
        self.assertContains(detail_response, ticket_url)

    def test_direct_post_cannot_exceed_event_ticket_limit(self):
        ticket_url = reverse('book_ticket', kwargs={'pk': self.event.pk})
        self.client.force_login(self.attendee)
        self.client.post(ticket_url, {'quantity': 2})

        self.client.force_login(self.other_attendee)
        response = self.client.post(ticket_url, {'quantity': 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only 1 tickets remaining')
        self.assertEqual(self.event.tickets_sold, 2)

    def test_sold_out_event_is_labelled_and_rejects_booking(self):
        Ticket.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=self.event.max_tickets,
        )
        self.client.force_login(self.other_attendee)

        list_response = self.client.get(reverse('event_list'))
        detail_response = self.client.get(
            reverse('event_detail', kwargs={'pk': self.event.pk})
        )
        post_response = self.client.post(
            reverse('book_ticket', kwargs={'pk': self.event.pk}),
            {'quantity': 1},
            follow=True,
        )

        self.assertContains(list_response, 'Sold out')
        self.assertContains(detail_response, 'Sold out')
        self.assertContains(post_response, 'This event is sold out')
        self.assertEqual(self.event.tickets_sold, self.event.max_tickets)

    def test_legacy_booking_still_uses_one_available_ticket(self):
        EventBooking.objects.create(user=self.attendee, event=self.event)

        self.assertEqual(self.event.tickets_remaining, 2)

    def test_attendee_can_view_own_tickets(self):
        Ticket.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=1,
        )
        self.client.force_login(self.attendee)

        # Test direct access to my_bookings
        response = self.client.get(reverse('my_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bookable Show')

# Test legacy my_tickets redirects to my_bookings
        legacy_response = self.client.get(reverse('my_tickets'), follow=True)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertContains(legacy_response, 'Bookable Show')

    def test_expired_event_shows_done_status_and_disables_booking(self):
        expired_event = Event.objects.create(
            organizer=self.organizer,
            title='Past Show',
            description='Already finished',
            date=timezone.now() - timedelta(days=1),
            price='20.00',
            max_tickets=5,
        )
        expired_event.categories.add(self.arts_category)
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('event_detail', kwargs={'pk': expired_event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Event Done')
        self.assertContains(response, 'Event done')
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
            reverse('login') + '?next=' + self.delete_url,
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
        self.music_category = Category.objects.create(name='Music', slug='music')
        self.tech_category = Category.objects.create(name='Tech', slug='tech')
        self.event1 = Event.objects.create(
            organizer=self.organizer,
            title='Delete Me 1',
            date=timezone.now() + timedelta(days=2),
            price='10.00',
        )
        self.event1.categories.add(self.music_category)
        self.event2 = Event.objects.create(
            organizer=self.organizer,
            title='Delete Me 2',
            date=timezone.now() + timedelta(days=2),
            price='20.00',
        )
        self.event2.categories.add(self.tech_category)
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

class EventListViewTest(TestCase):
    def setUp(self):
        now = timezone.now()
        self.tech_cat = Category.objects.create(name="Tech", slug="tech")
        self.music_cat = Category.objects.create(name="Music", slug="music")
        self.event1 = Event.objects.create(
            title="Tech Conference",
            description="All about technology",
            location="Berlin",
            date=now + timedelta(days=2),
            price=50.00,
        )
        self.event1.categories.add(self.tech_cat)
        self.event2 = Event.objects.create(
            title="Music Festival",
            description="Live music",
            location="London",
            date=now + timedelta(days=10),
            price=150.00,
        )
        self.event2.categories.add(self.music_cat)

    def test_event_list_view(self):
        response = self.client.get(reverse('event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/event_list.html')
        self.assertContains(response, "Tech Conference")
        self.assertContains(response, "Music Festival")
        self.assertContains(response, "All about technology")
        self.assertContains(response, "Grid")
        self.assertContains(response, "List")

    def test_event_list_filtering(self):
        start_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        
        response = self.client.get(reverse('event_list'), {
            'category': 'tech',
            'start_date': start_date,
            'end_date': end_date,
            'max_price': '100.00',
            'search': 'Tech'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech Conference")
        self.assertNotContains(response, "Music Festival")

    def test_event_list_location_and_sort(self):
        now = timezone.now()
        # Location filter test
        res_loc = self.client.get(reverse('event_list'), {'location': 'Berlin'})
        self.assertEqual(res_loc.status_code, 200)
        self.assertContains(res_loc, "Tech Conference")
        self.assertNotContains(res_loc, "Music Festival")

        # Sort test
        res_sort = self.client.get(reverse('event_list'), {'sort': 'date_desc'})
        self.assertEqual(res_sort.status_code, 200)
        events = list(res_sort.context['events'])
        self.assertEqual(events[0].title, "Music Festival")
        self.assertEqual(events[1].title, "Tech Conference")

    def test_event_list_excludes_past_events(self):
        organizer = User.objects.create_user(
            'past_test_org',
            'past_test_org@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        future_event = Event.objects.create(
            organizer=organizer,
            title="Future Event",
            date=timezone.now() + timedelta(days=1),
            price=10,
            max_tickets=10,
        )
        future_event.categories.add(self.tech_cat)

        past_event = Event.objects.create(
            organizer=organizer,
            title="Past Event",
            date=timezone.now() - timedelta(days=1),
            price=10,
            max_tickets=10,
        )
        past_event.categories.add(self.tech_cat)

        response = self.client.get(reverse("event_list"))
        self.assertContains(response, "Future Event")
        self.assertNotContains(response, "Past Event")

        # Past event can still be opened directly via event_detail
        detail_response = self.client.get(
            reverse("event_detail", kwargs={"pk": past_event.pk})
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Past Event")

    def test_event_api_list(self):
        response = self.client.get(reverse('event_api_list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) >= 2)
        self.assertIn('categories', data[0])
        self.assertIn('tickets_available', data[0])

    def test_event_page_api(self):
        response = self.client.get(reverse('event_page_api'), {'page': 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('grid_html', data)
        self.assertIn('list_html', data)
        self.assertIn('has_next', data)

    def test_event_list_displays_six_events_per_page(self):
        now = timezone.now()
        for i in range(3, 10):
            e = Event.objects.create(
                title=f"Event {i}",
                description=f"Description {i}",
                date=now + timedelta(days=i),
                price=10.00 * i,
            )
            e.categories.add(self.tech_cat)
        response = self.client.get(reverse('event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 6)
        self.assertEqual(response.context['paginator'].per_page, 6)
        self.assertContains(response, 'lg:grid-cols-3')


class BookingConfirmationEmailTests(TestCase):
    def setUp(self):
        self.attendee = User.objects.create_user(
            'email_attendee',
            'email_attendee@example.com',
            'strong-pass-123',
            role=UserRole.ATTENDEE,
        )
        self.organizer = User.objects.create_user(
            'email_organizer',
            'email_organizer@example.com',
            'strong-pass-123',
            role=UserRole.ORGANIZER,
        )
        self.music_cat = Category.objects.create(name='Email Music', slug='email-music')
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Email Concert',
            date=timezone.now() + timedelta(days=1),
            price=Decimal('25.00'),
            max_tickets=10,
        )
        self.event.categories.add(self.music_cat)
        self.ticket = Ticket.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=2,
        )

    def test_sends_confirmation_with_booking_details(self):
        from django.template.loader import render_to_string

        context = {
            'ticket': self.ticket,
            'unit_price': Decimal('25.00'),
            'total_price': Decimal('50.00'),
            'event_url': 'https://example.com/events/1/',
            'logo_src': '',
        }
        text_body = render_to_string(
            'events/booking_confirmation_email.txt',
            context,
        )
        html_body = render_to_string(
            'events/booking_confirmation_email.html',
            context,
        )

        self.assertIn('Email Concert', text_body)
        self.assertIn('Ticket Quantity: 2', text_body)
        self.assertIn('Total Price: 50.00', text_body)
        self.assertIn('$50.00', html_body)
        self.assertNotIn('cid:event-image', html_body)

    def test_confirmation_includes_full_total_for_one_ticket(self):
        from django.template.loader import render_to_string

        single_ticket = Ticket.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=1,
        )
        context = {
            'ticket': single_ticket,
            'unit_price': Decimal('25.00'),
            'total_price': Decimal('25.00'),
            'event_url': 'https://example.com/events/1/',
            'logo_src': '',
        }
        text_body = render_to_string(
            'events/booking_confirmation_email.txt',
            context,
        )
        html_body = render_to_string(
            'events/booking_confirmation_email.html',
            context,
        )

        self.assertIn('Ticket Quantity: 1', text_body)
        self.assertIn('Total Price: 25.00', text_body)
        self.assertIn('$25.00', html_body)
        self.assertNotIn('event_image_src', html_body)

    def test_logo_url_points_at_the_real_static_logo(self):
        from .emails import _absolute_url, _get_logo_src

        logo_src = _get_logo_src()
        joined = _absolute_url('static/images/eventify_no_background.png')

        self.assertTrue(logo_src.startswith('https://'))
        self.assertIn('/static/images/eventify_no_background.png', logo_src)
        self.assertNotIn('comstatic/', joined)
        self.assertTrue(joined.endswith('/static/images/eventify_no_background.png'))

    def test_requires_attendee_email(self):
        self.attendee.email = ''
        self.attendee.save()
        self.ticket.refresh_from_db()

        with self.assertRaises(ValueError):
            send_booking_confirmation_email(self.ticket)

        self.assertEqual(len(mail.outbox), 0)


class AnalyticsExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            username='export_org',
            email='export_org@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.admin = User.objects.create_user(
            username='export_admin',
            email='export_admin@example.com',
            password='Password123!',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.attendee = User.objects.create_user(
            username='export_att',
            email='export_att@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )

        self.category = Category.objects.create(
            name='Tech',
            slug='tech',
        )
        self.event1 = Event.objects.create(
            title='Tech Summit 2026',
            organizer=self.organizer,
            date=timezone.now() + timedelta(days=7),
            price=Decimal('50.00'),
            max_tickets=100,
            location='Istanbul Congress Center',
        )
        self.event1.categories.add(self.category)
        self.ticket1 = Ticket.objects.create(
            event=self.event1,
            attendee=self.attendee,
            quantity=5,
        )

    def test_organizer_can_export_excel(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment; filename="eventify_analytics_', response['Content-Disposition'])
        self.assertTrue(len(response.content) > 0)

    def test_organizer_can_export_pdf(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_export_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="eventify_analytics_', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_admin_can_export_excel_and_pdf(self):
        self.client.force_login(self.admin)
        excel_resp = self.client.get(reverse('organizer_export_excel'))
        self.assertEqual(excel_resp.status_code, 200)
        self.assertEqual(
            excel_resp['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        pdf_resp = self.client.get(reverse('organizer_export_pdf'))
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertTrue(pdf_resp.content.startswith(b'%PDF'))

    def test_attendee_cannot_export_analytics(self):
        self.client.force_login(self.attendee)
        excel_resp = self.client.get(reverse('organizer_export_excel'))
        self.assertEqual(excel_resp.status_code, 302)
        pdf_resp = self.client.get(reverse('organizer_export_pdf'))
        self.assertEqual(pdf_resp.status_code, 302)

    def test_unauthenticated_user_redirected_to_login(self):
        excel_resp = self.client.get(reverse('organizer_export_excel'))
        self.assertEqual(excel_resp.status_code, 302)
        pdf_resp = self.client.get(reverse('organizer_export_pdf'))
        self.assertEqual(pdf_resp.status_code, 302)
