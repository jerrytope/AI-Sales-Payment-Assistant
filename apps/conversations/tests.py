from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from apps.customers.models import Customer
from apps.conversations.models import Message


class WhatsAppWebhookViewTests(APITestCase):
    def test_webhook_creates_customer_and_saves_message(self):
        url = reverse("whatsapp-webhook")
        payload = {
            "From": "whatsapp:+2348012345678",
            "Body": "Hello, I want to inquire about products",
            "MessageSid": "SMmock123",
        }

        # Verify no customer exists initially
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)

        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert customer was created
        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.first()
        self.assertEqual(customer.phone_number, "+2348012345678")
        self.assertEqual(customer.workflow_state, Customer.WorkflowState.NEW_LEAD)

        # Assert message was saved
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.first()
        self.assertEqual(msg.customer, customer)
        self.assertEqual(msg.body, "Hello, I want to inquire about products")
        self.assertEqual(msg.direction, Message.Direction.INBOUND)
        self.assertEqual(msg.sender_type, Message.SenderType.USER)
        self.assertEqual(msg.twilio_sid, "SMmock123")

    def test_webhook_existing_customer_saves_message(self):
        # Setup existing customer
        customer = Customer.objects.create(
            phone_number="+2348012345678", workflow_state=Customer.WorkflowState.AWAITING_REPLY
        )

        url = reverse("whatsapp-webhook")
        payload = {
            "From": "whatsapp:+2348012345678",
            "Body": "Another message",
            "MessageSid": "SMmock124",
        }

        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check customer wasn't duplicated
        self.assertEqual(Customer.objects.count(), 1)
        # Check message saved
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.first()
        self.assertEqual(msg.customer, customer)
        self.assertEqual(msg.body, "Another message")

    @override_settings(TWILIO_VALIDATE_SIGNATURE=True, TWILIO_AUTH_TOKEN="testtoken")
    def test_webhook_missing_signature_forbidden(self):
        """Request fails with 403 when signature header is missing."""
        url = reverse("whatsapp-webhook")
        payload = {"From": "whatsapp:+2348012345678", "Body": "Hello"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(TWILIO_VALIDATE_SIGNATURE=True, TWILIO_AUTH_TOKEN="testtoken")
    def test_webhook_invalid_signature_forbidden(self):
        """Request fails with 403 when signature is invalid."""
        url = reverse("whatsapp-webhook")
        payload = {"From": "whatsapp:+2348012345678", "Body": "Hello"}
        response = self.client.post(url, payload, HTTP_X_TWILIO_SIGNATURE="invalid_sig")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.messaging.decorators.RequestValidator.validate")
    @override_settings(TWILIO_VALIDATE_SIGNATURE=True, TWILIO_AUTH_TOKEN="testtoken")
    def test_webhook_valid_signature_success(self, mock_validate):
        """Request succeeds with 200 when signature validation passes."""
        mock_validate.return_value = True
        url = reverse("whatsapp-webhook")
        payload = {
            "From": "whatsapp:+2348012345678",
            "Body": "Hello",
            "MessageSid": "SMmock125"
        }
        response = self.client.post(url, payload, HTTP_X_TWILIO_SIGNATURE="valid_sig")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_webhook_rejects_non_post_methods(self):
        """GET request to webhook view is rejected with 405 Method Not Allowed."""
        url = reverse("whatsapp-webhook")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_webhook_throttling_triggers_429(self):
        """Sending requests exceeding the rate limit triggers 429 Too Many Requests."""
        from rest_framework.settings import api_settings
        from django.core.cache import cache

        # Clear cache to avoid any leftover hits from other tests
        cache.clear()

        # Dynamically set the rate limit on api_settings
        original_rate = api_settings.DEFAULT_THROTTLE_RATES.get("webhook")
        api_settings.DEFAULT_THROTTLE_RATES["webhook"] = "1/day"

        try:
            url = reverse("whatsapp-webhook")
            payload = {
                "From": "whatsapp:+2348012345678",
                "Body": "First text",
                "MessageSid": "SM1"
            }

            with override_settings(TWILIO_VALIDATE_SIGNATURE=False):
                # First request should pass
                response1 = self.client.post(url, payload)
                self.assertEqual(response1.status_code, status.HTTP_200_OK)

                # Second request within the same day should fail with 429
                response2 = self.client.post(url, payload)
                self.assertEqual(response2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            # Restore original rate limit
            if original_rate:
                api_settings.DEFAULT_THROTTLE_RATES["webhook"] = original_rate
            else:
                api_settings.DEFAULT_THROTTLE_RATES.pop("webhook", None)


