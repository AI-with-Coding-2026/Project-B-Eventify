import os
import shutil
import tempfile
from decimal import Decimal
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from authentication.models import User, UserRole
from .forms import EventForm
from .models import Booking, Category, Event

# Create a temporary directory for MEDIA_ROOT during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class EventModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.organizer = User.objects.create_user(
            username='org_model_test',
            email='org_model@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )

    def test_create_event(self):
        event = Event.objects.create(
            organizer=self.organizer,
            title='Tech Conference 2026',
            description='Annual tech summit.',
            location='Convention Center',
            date=timezone.now() + timezone.timedelta(days=10),
            ticket_price=Decimal('49.99'),
            max_tickets=200,
        )
        self.assertEqual(str(event), 'Tech Conference 2026 by org_model_test')
        self.assertEqual(event.organizer, self.organizer)

    def test_event_categories_m2m(self):
        """Test that events can have multiple categories."""
        cat1 = Category.objects.create(name='Music')
        cat2 = Category.objects.create(name='Technology')
        event = Event.objects.create(
            organizer=self.organizer,
            title='Tech Music Fest',
            description='Fusion event.',
            location='Arena',
            date=timezone.now() + timezone.timedelta(days=10),
            ticket_price=Decimal('30.00'),
            max_tickets=500,
        )
        event.categories.add(cat1, cat2)
        self.assertEqual(event.categories.count(), 2)
        self.assertIn(cat1, event.categories.all())
        self.assertIn(cat2, event.categories.all())

    def test_category_auto_slug(self):
        """Test that Category auto-generates slug from name."""
        cat = Category.objects.create(name='Health & Wellness')
        self.assertEqual(cat.slug, 'health-wellness')

    def test_poster_file_deleted_on_event_delete(self):
        dummy_image = SimpleUploadedFile(
            name='test_poster.png',
            content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4',
            content_type='image/png',
        )
        event = Event.objects.create(
            organizer=self.organizer,
            title='Poster Delete Event',
            description='Test description',
            location='Online',
            date=timezone.now() + timezone.timedelta(days=5),
            ticket_price=Decimal('10.00'),
            max_tickets=50,
            poster=dummy_image,
        )
        poster_path = event.poster.path
        self.assertTrue(os.path.isfile(poster_path))

        # Delete event instance
        event.delete()
        self.assertFalse(os.path.isfile(poster_path))

    def test_old_poster_file_deleted_on_poster_update(self):
        image_1 = SimpleUploadedFile(
            name='poster_1.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00',
            content_type='image/jpeg',
        )
        image_2 = SimpleUploadedFile(
            name='poster_2.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00',
            content_type='image/jpeg',
        )
        event = Event.objects.create(
            organizer=self.organizer,
            title='Poster Update Event',
            description='Test description',
            location='Online',
            date=timezone.now() + timezone.timedelta(days=5),
            ticket_price=Decimal('10.00'),
            max_tickets=50,
            poster=image_1,
        )
        old_poster_path = event.poster.path
        self.assertTrue(os.path.isfile(old_poster_path))

        # Replace poster
        event.poster = image_2
        event.save()

        # Old file should be deleted, new file should exist
        self.assertFalse(os.path.isfile(old_poster_path))
        self.assertTrue(os.path.isfile(event.poster.path))


class EventFormTests(TestCase):
    def test_valid_form(self):
        data = {
            'title': 'Hackathon 2026',
            'description': '48-hour coding marathon.',
            'location': 'Innovation Hub',
            'date': (timezone.now() + timezone.timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '15.00',
            'max_tickets': 100,
        }
        form = EventForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_poster_extension(self):
        bad_file = SimpleUploadedFile(
            name='document.pdf',
            content=b'%PDF-1.4 fake pdf content',
            content_type='application/pdf',
        )
        data = {
            'title': 'PDF Poster Event',
            'description': 'Testing invalid extension',
            'location': 'Test City',
            'date': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '0.00',
            'max_tickets': 10,
        }
        files = {'poster': bad_file}
        form = EventForm(data=data, files=files)
        self.assertFalse(form.is_valid())
        self.assertIn('poster', form.errors)

    def test_invalid_poster_size(self):
        # Create a file larger than 5MB
        large_content = b'0' * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            name='large_image.jpg',
            content=large_content,
            content_type='image/jpeg',
        )
        data = {
            'title': 'Large Image Event',
            'description': 'Testing large image size',
            'location': 'Test City',
            'date': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '0.00',
            'max_tickets': 10,
        }
        files = {'poster': large_file}
        form = EventForm(data=data, files=files)
        self.assertFalse(form.is_valid())
        self.assertIn('poster', form.errors)

    def test_negative_ticket_price_rejected(self):
        data = {
            'title': 'Negative Price Event',
            'description': 'Testing negative price',
            'location': 'Test City',
            'date': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '-5.00',
            'max_tickets': 10,
        }
        form = EventForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_price', form.errors)

    def test_past_date_rejected(self):
        """Feature 5: Past dates should be rejected by form validation."""
        data = {
            'title': 'Past Date Event',
            'description': 'Testing past date',
            'location': 'Test City',
            'date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '10.00',
            'max_tickets': 10,
        }
        form = EventForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_date_beyond_six_months_rejected(self):
        """Feature 5: Dates more than 6 months in the future should be rejected."""
        data = {
            'title': 'Far Future Event',
            'description': 'Testing future date limit',
            'location': 'Test City',
            'date': (timezone.now() + timezone.timedelta(days=200)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '10.00',
            'max_tickets': 10,
        }
        form = EventForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_valid_date_within_range_accepted(self):
        """Feature 5: Dates within the valid range should be accepted."""
        data = {
            'title': 'Valid Date Event',
            'description': 'Testing valid date',
            'location': 'Test City',
            'date': (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '10.00',
            'max_tickets': 10,
        }
        form = EventForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class EventViewsAuthorizationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.organizer_a = User.objects.create_user(
            username='organizer_a',
            email='orga@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.organizer_b = User.objects.create_user(
            username='organizer_b',
            email='orgb@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            username='attendee_user',
            email='attendee@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )

        self.event_a = Event.objects.create(
            organizer=self.organizer_a,
            title="Organizer A's Concert",
            description='Concert description',
            location='Music Hall',
            date=timezone.now() + timezone.timedelta(days=3),
            ticket_price=Decimal('25.00'),
            max_tickets=150,
        )

    def test_organizer_a_can_view_own_event_list(self):
        self.client.force_login(self.organizer_a)
        response = self.client.get(reverse('organizer_event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organizer A&#x27;s Concert")

    def test_organizer_b_cannot_see_organizer_a_event_in_their_list(self):
        self.client.force_login(self.organizer_b)
        response = self.client.get(reverse('organizer_event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Organizer A&#x27;s Concert")

    def test_organizer_a_can_create_event(self):
        self.client.force_login(self.organizer_a)
        post_data = {
            'title': 'New Workshop',
            'description': 'Workshop details',
            'location': 'Room 101',
            'date': (timezone.now() + timezone.timedelta(days=4)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '20.00',
            'max_tickets': 30,
        }
        response = self.client.post(reverse('event_create'), post_data)
        self.assertRedirects(response, reverse('organizer_event_list'))
        self.assertTrue(Event.objects.filter(title='New Workshop', organizer=self.organizer_a).exists())

    def test_organizer_a_can_edit_own_event(self):
        self.client.force_login(self.organizer_a)
        edit_url = reverse('event_edit', kwargs={'pk': self.event_a.pk})
        post_data = {
            'title': "Organizer A's Concert (Updated)",
            'description': 'Updated description',
            'location': 'New Music Hall',
            'date': (timezone.now() + timezone.timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '30.00',
            'max_tickets': 200,
        }
        response = self.client.post(edit_url, post_data)
        self.assertRedirects(response, reverse('organizer_event_list'))

        self.event_a.refresh_from_db()
        self.assertEqual(self.event_a.title, "Organizer A's Concert (Updated)")
        self.assertEqual(self.event_a.location, 'New Music Hall')

    def test_organizer_b_cannot_edit_organizer_a_event(self):
        """Strict Ownership Authorization Test: Organizer B blocked from editing Organizer A's event."""
        self.client.force_login(self.organizer_b)
        edit_url = reverse('event_edit', kwargs={'pk': self.event_a.pk})
        post_data = {
            'title': "Hacked Event Title",
            'description': 'Malicious update attempt',
            'location': 'Hacked Location',
            'date': (timezone.now() + timezone.timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'ticket_price': '0.00',
            'max_tickets': 1,
        }
        response = self.client.post(edit_url, post_data)
        # Should be redirected to unauthorized page
        self.assertRedirects(response, reverse('unauthorized'))

        # Verify event was NOT changed
        self.event_a.refresh_from_db()
        self.assertEqual(self.event_a.title, "Organizer A's Concert")

    def test_organizer_b_cannot_delete_organizer_a_event(self):
        """Strict Ownership Authorization Test: Organizer B blocked from deleting Organizer A's event."""
        self.client.force_login(self.organizer_b)
        delete_url = reverse('event_delete', kwargs={'pk': self.event_a.pk})
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('unauthorized'))

        # Verify event still exists
        self.assertTrue(Event.objects.filter(pk=self.event_a.pk).exists())

    def test_organizer_a_can_delete_own_event(self):
        self.client.force_login(self.organizer_a)
        delete_url = reverse('event_delete', kwargs={'pk': self.event_a.pk})
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('organizer_event_list'))
        self.assertFalse(Event.objects.filter(pk=self.event_a.pk).exists())

    def test_attendee_cannot_access_event_crud(self):
        self.client.force_login(self.attendee)

        # List
        res_list = self.client.get(reverse('organizer_event_list'))
        self.assertRedirects(res_list, reverse('unauthorized'))

        # Create
        res_create = self.client.get(reverse('event_create'))
        self.assertRedirects(res_create, reverse('unauthorized'))

        # Edit
        res_edit = self.client.get(reverse('event_edit', kwargs={'pk': self.event_a.pk}))
        self.assertRedirects(res_edit, reverse('unauthorized'))

        # Delete
        res_delete = self.client.get(reverse('event_delete', kwargs={'pk': self.event_a.pk}))
        self.assertRedirects(res_delete, reverse('unauthorized'))

    def test_attendee_can_view_event_detail(self):
        self.client.force_login(self.attendee)
        detail_url = reverse('event_detail', kwargs={'pk': self.event_a.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organizer A&#x27;s Concert")

    def test_attendee_sees_upcoming_events_on_dashboard(self):
        """Feature 2: Only upcoming events should appear on the attendee dashboard."""
        self.client.force_login(self.attendee)
        dashboard_url = reverse('attendee_dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organizer A&#x27;s Concert")

    def test_past_events_excluded_from_attendee_dashboard(self):
        """Feature 2: Past events should NOT appear on the attendee dashboard."""
        past_event = Event.objects.create(
            organizer=self.organizer_a,
            title='Past Concert',
            description='Already happened',
            location='Old Venue',
            date=timezone.now() - timezone.timedelta(days=1),
            ticket_price=Decimal('10.00'),
            max_tickets=50,
        )
        self.client.force_login(self.attendee)
        dashboard_url = reverse('attendee_dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Past Concert')


class BookingModelTests(TestCase):
    """Tests for the Booking model."""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username='org_booking',
            email='org_booking@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            username='att_booking',
            email='att_booking@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Booking Test Event',
            description='Test event for bookings',
            location='Test Venue',
            date=timezone.now() + timezone.timedelta(days=7),
            ticket_price=Decimal('50.00'),
            max_tickets=100,
        )

    def test_create_booking(self):
        booking = Booking.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=3,
        )
        self.assertEqual(booking.event, self.event)
        self.assertEqual(booking.attendee, self.attendee)
        self.assertEqual(booking.quantity, 3)
        self.assertIsNotNone(booking.booked_at)

    def test_booking_str(self):
        booking = Booking.objects.create(
            event=self.event,
            attendee=self.attendee,
            quantity=2,
        )
        self.assertEqual(
            str(booking),
            'att_booking \u00d7 2 for Booking Test Event',
        )

    def test_booking_default_quantity(self):
        booking = Booking.objects.create(
            event=self.event,
            attendee=self.attendee,
        )
        self.assertEqual(booking.quantity, 1)

    def test_bookings_cascade_on_event_delete(self):
        Booking.objects.create(event=self.event, attendee=self.attendee, quantity=2)
        self.assertEqual(Booking.objects.count(), 1)
        self.event.delete()
        self.assertEqual(Booking.objects.count(), 0)

    def test_bookings_cascade_on_attendee_delete(self):
        Booking.objects.create(event=self.event, attendee=self.attendee, quantity=2)
        self.assertEqual(Booking.objects.count(), 1)
        self.attendee.delete()
        self.assertEqual(Booking.objects.count(), 0)


class BookingViewTests(TestCase):
    """Tests for the book_event view."""

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            username='org_view',
            email='org_view@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            username='att_view',
            email='att_view@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Bookable Event',
            description='Test event',
            location='Test Venue',
            date=timezone.now() + timezone.timedelta(days=7),
            ticket_price=Decimal('25.00'),
            max_tickets=10,
        )

    def test_attendee_can_book_tickets(self):
        self.client.force_login(self.attendee)
        response = self.client.post(
            reverse('book_event', kwargs={'pk': self.event.pk}),
            {'quantity': 3},
        )
        self.assertRedirects(response, reverse('event_detail', kwargs={'pk': self.event.pk}))
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.quantity, 3)
        self.assertEqual(booking.attendee, self.attendee)

    def test_overbooking_rejected(self):
        """Cannot book more tickets than remaining."""
        # Book 8 of 10
        Booking.objects.create(event=self.event, attendee=self.attendee, quantity=8)

        self.client.force_login(self.attendee)
        response = self.client.post(
            reverse('book_event', kwargs={'pk': self.event.pk}),
            {'quantity': 5},
        )
        self.assertRedirects(response, reverse('event_detail', kwargs={'pk': self.event.pk}))
        # Should still be only the original booking
        self.assertEqual(Booking.objects.count(), 1)

    def test_sold_out_rejected(self):
        """Cannot book when event is sold out."""
        Booking.objects.create(event=self.event, attendee=self.attendee, quantity=10)

        self.client.force_login(self.attendee)
        response = self.client.post(
            reverse('book_event', kwargs={'pk': self.event.pk}),
            {'quantity': 1},
        )
        self.assertRedirects(response, reverse('event_detail', kwargs={'pk': self.event.pk}))
        # Should still be only the original booking
        self.assertEqual(Booking.objects.count(), 1)

    def test_organizer_cannot_book(self):
        """Organizers should be redirected (unauthorized) when trying to book."""
        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse('book_event', kwargs={'pk': self.event.pk}),
            {'quantity': 1},
        )
        self.assertRedirects(response, reverse('unauthorized'))

    def test_get_request_redirects_to_detail(self):
        """GET requests to book_event should redirect to event detail."""
        self.client.force_login(self.attendee)
        response = self.client.get(
            reverse('book_event', kwargs={'pk': self.event.pk}),
        )
        self.assertRedirects(response, reverse('event_detail', kwargs={'pk': self.event.pk}))


class OrganizerDashboardAnalyticsTests(TestCase):
    """Tests for the organizer dashboard analytics view."""

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            username='org_dashboard',
            email='org_dash@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.other_organizer = User.objects.create_user(
            username='org_other',
            email='org_other@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            username='att_dashboard',
            email='att_dash@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )
        self.event1 = Event.objects.create(
            organizer=self.organizer,
            title='Dashboard Event 1',
            description='Test event 1',
            location='Venue 1',
            date=timezone.now() + timezone.timedelta(days=7),
            ticket_price=Decimal('10.00'),
            max_tickets=100,
        )
        self.event2 = Event.objects.create(
            organizer=self.organizer,
            title='Dashboard Event 2',
            description='Test event 2',
            location='Venue 2',
            date=timezone.now() + timezone.timedelta(days=14),
            ticket_price=Decimal('20.00'),
            max_tickets=50,
        )
        self.other_event = Event.objects.create(
            organizer=self.other_organizer,
            title='Other Organizer Event',
            description='Should not appear',
            location='Venue 3',
            date=timezone.now() + timezone.timedelta(days=21),
            ticket_price=Decimal('30.00'),
            max_tickets=200,
        )

    def test_dashboard_shows_correct_totals(self):
        """Dashboard should show accurate ticket and revenue totals."""
        Booking.objects.create(event=self.event1, attendee=self.attendee, quantity=5)
        Booking.objects.create(event=self.event2, attendee=self.attendee, quantity=3)

        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context['total_events'], 2)
        self.assertEqual(context['total_tickets_sold'], 8)
        # event1: 5 * 10 = 50, event2: 3 * 20 = 60 → total 110
        self.assertEqual(context['total_revenue'], Decimal('110.00'))

    def test_dashboard_does_not_show_other_organizer_events(self):
        """Organizer should only see their own events."""
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

        event_titles = [stat['event'].title for stat in response.context['event_stats']]
        self.assertIn('Dashboard Event 1', event_titles)
        self.assertIn('Dashboard Event 2', event_titles)
        self.assertNotIn('Other Organizer Event', event_titles)

    def test_dashboard_with_no_bookings(self):
        """Dashboard should show zero totals when there are no bookings."""
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context['total_tickets_sold'], 0)
        self.assertEqual(context['total_revenue'], Decimal('0.00'))

    def test_per_event_stats(self):
        """Each event should have correct sold/remaining/revenue stats."""
        Booking.objects.create(event=self.event1, attendee=self.attendee, quantity=10)

        self.client.force_login(self.organizer)
        response = self.client.get(reverse('organizer_dashboard'))

        event_stats = {
            stat['event'].pk: stat for stat in response.context['event_stats']
        }

        stat1 = event_stats[self.event1.pk]
        self.assertEqual(stat1['tickets_sold'], 10)
        self.assertEqual(stat1['tickets_remaining'], 90)
        self.assertEqual(stat1['revenue'], Decimal('100.00'))

        stat2 = event_stats[self.event2.pk]
        self.assertEqual(stat2['tickets_sold'], 0)
        self.assertEqual(stat2['tickets_remaining'], 50)
        self.assertEqual(stat2['revenue'], Decimal('0.00'))

    def test_attendee_cannot_access_organizer_dashboard(self):
        """Attendees should be redirected from the organizer dashboard."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertRedirects(response, reverse('unauthorized'))

    def test_event_detail_shows_tickets_remaining(self):
        """Event detail should show accurate remaining ticket count."""
        Booking.objects.create(event=self.event1, attendee=self.attendee, quantity=7)

        self.client.force_login(self.attendee)
        response = self.client.get(
            reverse('event_detail', kwargs={'pk': self.event1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tickets_remaining'], 93)
        self.assertEqual(response.context['tickets_sold'], 7)


class AttendeeFilterTests(TestCase):
    """Tests for attendee dashboard filtering and sorting (Feature 3)."""

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            username='org_filter',
            email='org_filter@example.com',
            password='Password123!',
            role=UserRole.ORGANIZER,
        )
        self.attendee = User.objects.create_user(
            username='att_filter',
            email='att_filter@example.com',
            password='Password123!',
            role=UserRole.ATTENDEE,
        )
        self.cat_music = Category.objects.create(name='FilterMusic')
        self.cat_tech = Category.objects.create(name='FilterTech')

        self.event_ny = Event.objects.create(
            organizer=self.organizer,
            title='NY Music Fest',
            description='Music in NY',
            location='New York',
            date=timezone.now() + timezone.timedelta(days=5),
            ticket_price=Decimal('20.00'),
            max_tickets=100,
        )
        self.event_ny.categories.add(self.cat_music)

        self.event_la = Event.objects.create(
            organizer=self.organizer,
            title='LA Tech Conf',
            description='Tech in LA',
            location='Los Angeles',
            date=timezone.now() + timezone.timedelta(days=10),
            ticket_price=Decimal('30.00'),
            max_tickets=200,
        )
        self.event_la.categories.add(self.cat_tech)

    def test_location_filter(self):
        """Feature 3: Filter events by location."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('attendee_dashboard'), {'location': 'New York'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NY Music Fest')
        self.assertNotContains(response, 'LA Tech Conf')

    def test_category_filter(self):
        """Feature 3: Filter events by category."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('attendee_dashboard'), {'category': self.cat_tech.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LA Tech Conf')
        self.assertNotContains(response, 'NY Music Fest')

    def test_sort_date_asc(self):
        """Feature 3: Sort events soonest first."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('attendee_dashboard'), {'sort': 'date_asc'})
        events_list = list(response.context['events'])
        self.assertEqual(events_list[0].title, 'NY Music Fest')

    def test_sort_date_desc(self):
        """Feature 3: Sort events latest first."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse('attendee_dashboard'), {'sort': 'date_desc'})
        events_list = list(response.context['events'])
        self.assertEqual(events_list[0].title, 'LA Tech Conf')

    def test_ajax_infinite_scroll_returns_json(self):
        """Feature 8: AJAX requests should return JSON with html and has_next."""
        self.client.force_login(self.attendee)
        response = self.client.get(
            reverse('attendee_dashboard'),
            {'page': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('html', data)
        self.assertIn('has_next', data)
