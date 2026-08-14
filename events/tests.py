from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from authentication.models import User, UserRole

from .models import Category, Event


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


class EventDetailBackButtonTests(TestCase):
    """Verify the back button on the event detail page uses the correct
    label and URL based on where the user navigated from."""

    def setUp(self):
        self.event = Event.objects.create(
            title='Back Button Event',
            description='Testing back navigation',
            date=timezone.now() + timedelta(days=5),
            price=25.00,
            category='tech',
        )
        self.detail_url = reverse('event_detail', kwargs={'pk': self.event.pk})

    def test_defaults_to_event_list_without_referer(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to Events')
        self.assertContains(response, reverse('event_list'))

    def test_back_to_admin_dashboard(self):
        referer = 'http://testserver/admin/'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to Admin Dashboard')

    def test_back_to_organizer_dashboard(self):
        referer = 'http://testserver/dashboard/organizer/'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to Organizer Dashboard')

    def test_back_to_attendee_dashboard(self):
        referer = 'http://testserver/dashboard/attendee/'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to Attendee Dashboard')

    def test_back_to_my_events(self):
        referer = 'http://testserver/events/mine/'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to My Events')

    def test_back_to_filtered_event_list(self):
        referer = 'http://testserver/events/?category=tech&page=2'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to Events')
        # HTML escapes & to &amp; in attribute values.
        self.assertContains(response, 'category=tech&amp;page=2')

    def test_ignores_external_referer(self):
        referer = 'https://evil.example.com/phishing/'
        response = self.client.get(self.detail_url, HTTP_REFERER=referer)
        self.assertContains(response, 'Back to Events')
        self.assertContains(response, reverse('event_list'))