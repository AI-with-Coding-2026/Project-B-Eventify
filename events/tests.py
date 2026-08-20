from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from events.models import Event

User = get_user_model()


class EventOwnershipTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345!")
        self.bob = User.objects.create_user("bob", password="pw12345!")
        self.event = Event.objects.create(
            organizer=self.alice,
            title="Alice's Show",
            description="desc",
            location="Istanbul",
            date=timezone.now() + timezone.timedelta(days=5),
            ticket_price=Decimal("50.00"),
            max_tickets=100,
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("events:event_list"))
        self.assertEqual(response.status_code, 302)

    def test_organizer_sees_only_own_events(self):
        self.client.login(username="alice", password="pw12345!")
        response = self.client.get(reverse("events:event_list"))
        self.assertContains(response, "Alice&#x27;s Show")

        self.client.logout()
        self.client.login(username="bob", password="pw12345!")
        response = self.client.get(reverse("events:event_list"))
        self.assertNotContains(response, "Alice&#x27;s Show")

    def test_bob_cannot_edit_alices_event(self):
        self.client.login(username="bob", password="pw12345!")
        response = self.client.get(reverse("events:event_edit", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:event_list"))

    def test_bob_cannot_delete_alices_event(self):
        self.client.login(username="bob", password="pw12345!")
        response = self.client.post(reverse("events:event_delete", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:event_list"))
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())


class DashboardCalculationTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user("carol", password="pw12345!")
        self.event = Event.objects.create(
            organizer=self.organizer,
            title="Concert",
            description="desc",
            location="Ankara",
            date=timezone.now() + timezone.timedelta(days=3),
            ticket_price=Decimal("20.00"),
            max_tickets=10,
        )
        Booking.objects.create(
            event=self.event, customer_name="X", customer_email="x@example.com", quantity=3
        )
        Booking.objects.create(
            event=self.event, customer_name="Y", customer_email="y@example.com", quantity=2
        )

    def test_dashboard_math(self):
        self.assertEqual(self.event.tickets_sold, 5)
        self.assertEqual(self.event.tickets_remaining, 5)
        self.assertEqual(self.event.revenue, Decimal("100.00"))

        self.client.login(username="carol", password="pw12345!")
        response = self.client.get(reverse("events:dashboard"))
        self.assertContains(response, "100.00")
