from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse

from authentication.models import User, UserRole

from django.utils import timezone

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

    def test_organizer_can_enter_custom_category_when_other_is_selected(self):
        self.client.force_login(self.organizer_a)

        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'Comedy Night',
                'description': 'Stand up',
                'date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'price': '20.00',
                'category': 'other',
                'custom_category': 'Comedy',
            },
        )

        self.assertRedirects(response, reverse('organizer_event_list'))
        event = Event.objects.get(title='Comedy Night')
        self.assertEqual(event.category, 'other')
        self.assertEqual(event.custom_category, 'Comedy')
        self.assertEqual(event.category_label, 'Comedy')

    def test_other_category_requires_custom_name(self):
        self.client.force_login(self.organizer_a)

        response = self.client.post(
            reverse('event_create'),
            {
                'title': 'Needs Category',
                'description': 'Missing custom name',
                'date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'price': '10.00',
                'category': 'other',
                'custom_category': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a category name.')
        self.assertFalse(Event.objects.filter(title='Needs Category').exists())

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
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Bookable Show',
            description='Open for booking',
            date=timezone.now(),
            price='25.00',
            category='arts',
            max_tickets=3,
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
        self.assertContains(response, 'Only 1 ticket(s) remain')
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

        Category.objects.create(name='Cat 1')
        Category.objects.create(name='Cat 2')

    def test_admin_can_view_category_list(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('category_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cat 1')
        self.assertContains(response, 'Cat 2')


class EventListViewTest(TestCase):
    def setUp(self):
        now = timezone.now()
        self.event1 = Event.objects.create(
            title="Tech Conference",
            description="All about technology",
            date=now + timedelta(days=2),
            price=50.00,
            category="tech"
        )
        self.event2 = Event.objects.create(
            title="Music Festival",
            description="Live music",
            date=now + timedelta(days=10),
            price=150.00,
            category="music"
        )

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
