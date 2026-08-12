    def test_admin_dashboard_displays_organizers_and_attendees(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('organizers', response.context)
        self.assertIn('attendees', response.context)

        organizers = response.context['organizers']
        attendees = response.context['attendees']

        self.assertIn(self.organizer, organizers)
        self.assertIn(self.attendee, attendees)
        self.assertNotIn(self.admin_user, organizers)
        self.assertNotIn(self.admin_user, attendees)

        # Verify rendered content
        self.assertContains(response, 'Organizers')
        self.assertContains(response, 'Attendees')
        self.assertContains(response, self.organizer.username)
        self.assertContains(response, self.attendee.username)

    def test_admin_dashboard_denies_organizer_with_unauthorized(self):
        """Organizer accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('admin_dashboard'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_admin_dashboard_denies_attendee_with_unauthorized(self):
        """Attendee accessing admin dashboard gets redirected to /unauthorized/ (403)."""
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('admin_dashboard'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_custom_admin_site_is_mounted_and_restricted_to_admin_role(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('eventify_admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Eventify Administration')

    def test_admin_role_can_view_users_in_custom_admin_site(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('eventify_admin:authentication_user_changelist')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.organizer.username)

    def test_custom_admin_site_denies_organizer_with_unauthorized(self):
        """Organizer accessing /admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('eventify_admin:index'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')

    def test_custom_admin_site_denies_attendee_with_unauthorized(self):
        """Attendee accessing /admin/ gets redirected to /unauthorized/ (403), not 404."""
        self.client.force_login(self.attendee)

        response = self.client.get(reverse('eventify_admin:index'), follow=True)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'authentication/unauthorized.html')