import json
import hmac
import hashlib
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from apps.customers.models import Customer
from apps.payments.models import Order
from apps.payments.paystack import PaystackClient


class PaystackClientTests(APITestCase):
    @patch("apps.payments.paystack.requests.post")
    def test_initialize_transaction(self, mock_post):
        # Mock Response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": True,
            "message": "Authorization URL created",
            "data": {
                "authorization_url": "https://checkout.paystack.com/mock-url",
                "access_code": "access_123",
                "reference": "REF123",
            },
        }
        mock_post.return_value = mock_response

        with override_settings(
            PAYSTACK_SECRET_KEY="test_secret",
            PAYSTACK_CALLBACK_URL="http://localhost:8000/callback/",
        ):
            client = PaystackClient()
            data = client.initialize_transaction(
                email="test@example.com", amount=500000, reference="REF123"
            )

            self.assertEqual(data["authorization_url"], "https://checkout.paystack.com/mock-url")
            self.assertEqual(data["access_code"], "access_123")
            self.assertEqual(data["reference"], "REF123")


class PaystackWebhookViewTests(APITestCase):
    def setUp(self):
        self.secret_key = "test_secret_key"
        self.customer = Customer.objects.create(
            phone_number="+2348012345678",
            name="John Doe",
            workflow_state=Customer.WorkflowState.PENDING_PAYMENT,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            amount_kobo=500000,
            paystack_reference="SALE-REF-123",
            status=Order.Status.PENDING,
        )
        self.url = reverse("paystack-webhook")

    def _get_signature(self, payload_bytes: bytes) -> str:
        return hmac.new(self.secret_key.encode("utf-8"), payload_bytes, hashlib.sha512).hexdigest()

    @patch("apps.payments.views.TwilioWhatsAppClient")
    @override_settings(PAYSTACK_SECRET_KEY="test_secret_key")
    def test_webhook_successful_payment(self, mock_twilio_client_class):
        # Mock Twilio client
        mock_twilio = MagicMock()
        mock_twilio_client_class.return_value = mock_twilio

        payload = {
            "event": "charge.success",
            "data": {
                "reference": "SALE-REF-123",
                "amount": 500000,
                "status": "success",
                "customer": {"email": "test@example.com"},
            },
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._get_signature(payload_bytes)

        # Send request
        response = self.client.post(
            self.url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from db
        self.order.refresh_from_db()
        self.customer.refresh_from_db()

        # Assert status updates
        self.assertEqual(self.order.status, Order.Status.SUCCESS)
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.PAID)

        # Assert Twilio sent receipt message
        mock_twilio.send_message.assert_called_once()
        sent_body = mock_twilio.send_message.call_args[0][1]
        self.assertIn("Payment Confirmed", sent_body)
        self.assertIn("John Doe", sent_body)
        self.assertIn("₦5,000.00", sent_body)

    @override_settings(PAYSTACK_SECRET_KEY="test_secret_key")
    def test_webhook_invalid_signature_fails(self):
        payload = {"event": "charge.success", "data": {"reference": "SALE-REF-123"}}
        payload_bytes = json.dumps(payload).encode("utf-8")

        response = self.client.post(
            self.url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="invalid_sig_here",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify no database state changes
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_webhook_rejects_non_post_methods(self):
        """GET request to payments webhook is rejected with 405 Method Not Allowed."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
