from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from authentication.models import User, UserRole

from .models import Event

from io import BytesIO

from PIL import Image


def create_test_image():
    image = Image.new("RGB", (100, 100), "white")

    image_io = BytesIO()
    image.save(image_io, format="JPEG")

    image_io.seek(0)

    return SimpleUploadedFile(
        "test.jpg",
        image_io.read(),
        content_type="image/jpeg",
    )


class EventManTestSetup(TestCase):

    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer1",
            email="organizer1@example.com",
            password="strong-pass-123",
            role=UserRole.ORGANIZER,
        )

        self.organizer2 = User.objects.create_user(
            username="organizer2",
            email="organizer2@example.com",
            password="strong-pass-123",
            role=UserRole.ORGANIZER,
        )

        self.attendee = User.objects.create_user(
            username="attendee1",
            email="attendee1@example.com",
            password="strong-pass-123",
            role=UserRole.ATTENDEE,
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            title="Test Event",
            description="This is a test event.",
            location="Istanbul",
            date="2026-12-01T18:00:00Z",
            ticket_price=50.00,
            max_tickets=100,
            poster=create_test_image(),
        )


class OrganizerEventListTests(EventManTestSetup):

    def test_organizer_can_view_event_list(self):
        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse("organizer_event_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Event")

    def test_organizer_only_sees_own_events(self):
        Event.objects.create(
            organizer=self.organizer2,
            title="Other Organizer Event",
            description="Another event.",
            location="Ankara",
            date="2026-12-02T18:00:00Z",
            ticket_price=25.00,
            max_tickets=50,
            poster=create_test_image(),
        )

        self.client.force_login(self.organizer)

        response = self.client.get(
            reverse("organizer_event_list")
        )

        self.assertContains(response, "Test Event")
        self.assertNotContains(response, "Other Organizer Event")


class CreateEventTests(EventManTestSetup):

    def test_organizer_can_create_event(self):
        self.client.force_login(self.organizer)

        response = self.client.post(
            reverse("create_event"),
            {
                "title": "New Event",
                "description": "A newly created event.",
                "location": "Izmir",
                "date": "2026-12-10T18:00",
                "ticket_price": "75.00",
                "max_tickets": "200",
                "poster": create_test_image(),
            },
        )

        if response.status_code != 302:
            print(
                "CREATE FORM ERRORS:",
                response.context["form"].errors
            )

        self.assertRedirects(
            response,
            reverse("organizer_event_list")
        )

        event = Event.objects.get(title="New Event")

        self.assertEqual(
            event.organizer,
            self.organizer
        )


class EditEventTests(EventManTestSetup):

    def test_organizer_can_edit_own_event(self):
        self.client.force_login(self.organizer)

        response = self.client.post(
            reverse(
                "edit_event",
                args=[self.event.id]
            ),
            {
                "title": "Updated Event",
                "description": "Updated description.",
                "location": "Bursa",
                "date": "2026-12-15T18:00",
                "ticket_price": "100.00",
                "max_tickets": "150",
                "poster": create_test_image(),
            },
        )

        if response.status_code != 302:
            print(
                "EDIT FORM ERRORS:",
                response.context["form"].errors
            )

        self.assertRedirects(
            response,
            reverse("organizer_event_list")
        )

        self.event.refresh_from_db()

        self.assertEqual(
            self.event.title,
            "Updated Event"
        )

        self.assertEqual(
            self.event.organizer,
            self.organizer
        )

    def test_organizer_cannot_edit_another_organizers_event(self):
        self.client.force_login(self.organizer2)

        response = self.client.get(
            reverse(
                "edit_event",
                args=[self.event.id]
            )
        )

        self.assertEqual(response.status_code, 404)


class DeleteEventTests(EventManTestSetup):

    def test_organizer_can_delete_own_event(self):
        self.client.force_login(self.organizer)

        response = self.client.post(
            reverse(
                "delete_event",
                args=[self.event.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("organizer_event_list")
        )

        self.assertFalse(
            Event.objects.filter(
                id=self.event.id
            ).exists()
        )

    def test_organizer_cannot_delete_another_organizers_event(self):
        self.client.force_login(self.organizer2)

        response = self.client.post(
            reverse(
                "delete_event",
                args=[self.event.id]
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Event.objects.filter(
                id=self.event.id
            ).exists()
        )


class OrganizerAccessTests(EventManTestSetup):

    def test_attendee_cannot_manage_events(self):
        self.client.force_login(self.attendee)

        response = self.client.get(
            reverse("organizer_event_list")
        )

        self.assertRedirects(
            response,
            reverse("unauthorized")
        )