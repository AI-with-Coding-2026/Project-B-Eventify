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
from .models import Event

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

    def test_attendee_sees_created_events_on_dashboard(self):
        self.client.force_login(self.attendee)
        dashboard_url = reverse('attendee_dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organizer A&#x27;s Concert")

