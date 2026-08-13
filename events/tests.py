from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from events.models import Event

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
        self.assertContains(response, "Category:</strong> Tech")

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
