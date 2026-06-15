from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class DashboardViewsTestCase(TestCase):
    def setUp(self):
        self.username = "admin_user"
        self.password = "securepassword123"
        self.user = User.objects.create_superuser(
            username=self.username,
            email="admin@example.com",
            password=self.password
        )

    def test_dashboard_home_unauthenticated_redirects(self):
        """Unauthenticated requests to dashboard home redirect to login."""
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, f"/admin/login/?next={reverse('dashboard:home')}")

    def test_dashboard_home_authenticated_redirects(self):
        """Authenticated requests to dashboard home redirect to conversations."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, reverse("dashboard:conversations"))

    def test_conversations_view_unauthenticated(self):
        """Unauthenticated request to conversations redirects to login."""
        response = self.client.get(reverse("dashboard:conversations"))
        self.assertRedirects(response, f"/admin/login/?next={reverse('dashboard:conversations')}")

    def test_conversations_view_authenticated(self):
        """Authenticated user gets the conversations view."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:conversations"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/conversations.html")
        self.assertEqual(response.context["active_tab"], "conversations")

    def test_payments_view_unauthenticated(self):
        """Unauthenticated request to payments redirects to login."""
        response = self.client.get(reverse("dashboard:payments"))
        self.assertRedirects(response, f"/admin/login/?next={reverse('dashboard:payments')}")

    def test_payments_view_authenticated(self):
        """Authenticated user gets the payments view."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:payments"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/payments.html")
        self.assertEqual(response.context["active_tab"], "payments")

    def test_settings_view_unauthenticated(self):
        """Unauthenticated request to settings redirects to login."""
        response = self.client.get(reverse("dashboard:settings"))
        self.assertRedirects(response, f"/admin/login/?next={reverse('dashboard:settings')}")

    def test_settings_view_authenticated(self):
        """Authenticated user gets the settings view."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/settings.html")
        self.assertEqual(response.context["active_tab"], "settings")
