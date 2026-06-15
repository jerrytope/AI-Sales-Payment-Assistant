import json
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.utils import timezone
from apps.customers.models import Customer
from apps.conversations.models import Message
from apps.payments.models import Order
from apps.workflows.state_machine import WorkflowEngine
from apps.workflows.tasks import send_follow_up, send_payment_reminder


class WorkflowEngineTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            phone_number="+2348012345678",
            name="John Doe",
            workflow_state=Customer.WorkflowState.NEW_LEAD,
        )

    def test_state_transitions(self):
        engine = WorkflowEngine(self.customer)

        # Valid transition: NEW_LEAD -> AWAITING_REPLY
        success = engine.transition_to(Customer.WorkflowState.AWAITING_REPLY)
        self.assertTrue(success)
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.AWAITING_REPLY)

        # Invalid transition: AWAITING_REPLY -> PAID (not directly allowed)
        success = engine.transition_to(Customer.WorkflowState.PAID)
        self.assertFalse(success)
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.AWAITING_REPLY)

    @patch("apps.workflows.state_machine.TwilioWhatsAppClient")
    @patch("apps.workflows.tasks.send_follow_up.apply_async")
    def test_process_greeting_as_new_lead(self, mock_apply_async, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        engine = WorkflowEngine(self.customer)
        engine.process("GREETING", "Hello")

        # Customer should transition to AWAITING_REPLY
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.AWAITING_REPLY)

        # Welcome message should be sent
        mock_twilio.send_message.assert_called_once()
        self.assertIn("Welcome to", mock_twilio.send_message.call_args[0][1])

        # Message is saved as outbound
        self.assertEqual(Message.objects.filter(direction=Message.Direction.OUTBOUND).count(), 1)

        # Celery task should be scheduled
        mock_apply_async.assert_called_once_with(args=[self.customer.id], countdown=6 * 3600)

    @patch("apps.workflows.state_machine.TwilioWhatsAppClient")
    @patch("apps.workflows.state_machine.PaystackClient")
    @patch("apps.workflows.tasks.send_payment_reminder.apply_async")
    def test_process_buying_intent(
        self, mock_send_reminder_async, mock_paystack_client_class, mock_twilio_client_class
    ):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        mock_paystack = MagicMock()
        mock_paystack.initialize_transaction.return_value = {
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "access-123",
            "reference": "SALE-REF-123",
        }
        mock_paystack_client_class.return_value = mock_paystack

        self.customer.workflow_state = Customer.WorkflowState.NEW_LEAD
        self.customer.save()

        engine = WorkflowEngine(self.customer)
        engine.process("BUYING_INTENT", "I want to buy")

        # Verify state transitions to PENDING_PAYMENT
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.PENDING_PAYMENT)

        # Verify Order is created
        order = Order.objects.get(customer=self.customer)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_url, "https://checkout.paystack.com/test")

        # Verify Twilio sent link
        mock_twilio.send_message.assert_called_once()
        self.assertIn("https://checkout.paystack.com/test", mock_twilio.send_message.call_args[0][1])

    @patch("apps.workflows.state_machine.TwilioWhatsAppClient")
    def test_process_escalation(self, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        engine = WorkflowEngine(self.customer)
        engine.process("SUPPORT_OR_HUMAN", "I need help")

        self.customer.refresh_from_db()
        self.assertTrue(self.customer.human_takeover)
        self.assertEqual(self.customer.workflow_state, Customer.WorkflowState.ESCALATED)
        mock_twilio.send_message.assert_called_once()


class CeleryWorkflowTasksTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            phone_number="+2348012345678",
            workflow_state=Customer.WorkflowState.AWAITING_REPLY,
            follow_up_count=0,
        )

    @patch("apps.messaging.twilio_client.TwilioWhatsAppClient")
    @patch("apps.workflows.tasks.send_follow_up.apply_async")
    def test_send_follow_up_success(self, mock_apply_async, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        # Execute Celery task directly
        send_follow_up(self.customer.id)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.follow_up_count, 1)
        mock_twilio.send_message.assert_called_once()
        self.assertEqual(Message.objects.filter(direction=Message.Direction.OUTBOUND).count(), 1)

    @patch("apps.messaging.twilio_client.TwilioWhatsAppClient")
    def test_send_follow_up_aborts_if_state_changed(self, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        # Change state
        self.customer.workflow_state = Customer.WorkflowState.PAID
        self.customer.save()

        send_follow_up(self.customer.id)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.follow_up_count, 0)
        mock_twilio.send_message.assert_not_called()

    @patch("apps.messaging.twilio_client.TwilioWhatsAppClient")
    def test_send_follow_up_stops_after_3_attempts(self, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        self.customer.follow_up_count = 3
        self.customer.save()

        send_follow_up(self.customer.id)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.follow_up_count, 3)
        mock_twilio.send_message.assert_not_called()

    @patch("apps.messaging.twilio_client.TwilioWhatsAppClient")
    def test_send_payment_reminder_aborts_if_paid(self, mock_twilio_client_class):
        mock_twilio = MagicMock()
        mock_twilio.send_message.return_value = "SMmock123"
        mock_twilio_client_class.return_value = mock_twilio

        order = Order.objects.create(
            customer=self.customer,
            amount_kobo=500000,
            paystack_reference="SALE-REF-999",
            status=Order.Status.SUCCESS,
        )

        send_payment_reminder(order.id)

        order.refresh_from_db()
        self.assertEqual(order.reminder_count, 0)
        mock_twilio.send_message.assert_not_called()


from rest_framework.test import APITestCase
from rest_framework import status
import hmac
import hashlib


class EndToEndFlowTests(APITestCase):
    def setUp(self):
        from rest_framework.settings import api_settings
        self.original_rate = api_settings.DEFAULT_THROTTLE_RATES.get("webhook")
        api_settings.DEFAULT_THROTTLE_RATES["webhook"] = "1000/second"

        self.whatsapp_url = reverse("whatsapp-webhook")
        self.payments_url = reverse("paystack-webhook")
        self.phone = "+2348012345678"

    def tearDown(self):
        from rest_framework.settings import api_settings
        if self.original_rate:
            api_settings.DEFAULT_THROTTLE_RATES["webhook"] = self.original_rate
        else:
            api_settings.DEFAULT_THROTTLE_RATES.pop("webhook", None)

    @patch("apps.messaging.twilio_client.Client")
    @patch("apps.ai_engine.intent_classifier.model")
    @patch("apps.payments.paystack.requests.post")
    @patch("apps.workflows.tasks.send_follow_up.apply_async")
    @patch("apps.workflows.tasks.send_payment_reminder.apply_async")
    @override_settings(PAYSTACK_SECRET_KEY="test_secret_key")
    def test_happy_path_e2e(
        self,
        mock_reminder_async,
        mock_follow_up_async,
        mock_paystack_post,
        mock_gemini_model,
        mock_twilio_client_class,
    ):
        # 1. Setup Twilio Mock
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SMmock123"
        mock_client.messages.create.return_value = mock_message
        mock_twilio_client_class.return_value = mock_client

        # Mock Gemini for Greeting
        mock_response_greeting = MagicMock()
        mock_response_greeting.text = (
            '{"intent": "GREETING", "confidence": 0.9, '
            '"reply": "Welcome to our store", "product_interest": null}'
        )

        # Mock Gemini for Buying Intent
        mock_response_buying = MagicMock()
        mock_response_buying.text = (
            '{"intent": "BUYING_INTENT", "confidence": 0.95, '
            '"reply": "Sure, here is the checkout link", "product_interest": "item"}'
        )

        # We configure model.generate_content to return different values on sequential calls
        mock_gemini_model.generate_content.side_effect = [
            mock_response_greeting,
            mock_response_buying,
        ]

        # Mock Paystack initialize
        mock_paystack_response = MagicMock()
        mock_paystack_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/e2e-url",
                "access_code": "e2e-access",
                "reference": "SALE-E2E-REF",
            },
        }
        mock_paystack_post.return_value = mock_paystack_response

        # --- STEP 1: Inbound Greeting ---
        payload_greet = {
            "From": f"whatsapp:{self.phone}",
            "Body": "Hello!",
            "MessageSid": "SMgreet123",
        }
        response = self.client.post(self.whatsapp_url, payload_greet)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert customer created and in AWAITING_REPLY state
        customer = Customer.objects.get(phone_number=self.phone)
        self.assertEqual(customer.workflow_state, Customer.WorkflowState.AWAITING_REPLY)

        # Welcome message sent and follow up scheduled
        mock_client.messages.create.assert_called_once()
        mock_follow_up_async.assert_called_once_with(args=[customer.id], countdown=6 * 3600)

        mock_client.messages.create.reset_mock()

        # --- STEP 2: Inbound Buying Intent ---
        payload_buy = {
            "From": f"whatsapp:{self.phone}",
            "Body": "I want to buy your product",
            "MessageSid": "SMbuy123",
        }
        response = self.client.post(self.whatsapp_url, payload_buy)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Customer should transition to PENDING_PAYMENT
        customer.refresh_from_db()
        self.assertEqual(customer.workflow_state, Customer.WorkflowState.PENDING_PAYMENT)

        # Order should exist
        order = Order.objects.get(customer=customer)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.paystack_reference.startswith(f"SALE-{customer.id}-"))

        # Payment link sent and reminders scheduled
        mock_client.messages.create.assert_called_once()
        self.assertEqual(mock_reminder_async.call_count, 3)

        mock_client.messages.create.reset_mock()

        # --- STEP 3: Paystack Payment Webhook ---
        webhook_payload = {
            "event": "charge.success",
            "data": {
                "reference": order.paystack_reference,
                "amount": 500000,
                "status": "success",
                "customer": {"email": "customer@example.com"},
            },
        }
        payload_bytes = json.dumps(webhook_payload).encode("utf-8")
        signature = hmac.new(
            "test_secret_key".encode("utf-8"), payload_bytes, hashlib.sha512
        ).hexdigest()

        response = self.client.post(
            self.payments_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Customer state should be PAID
        customer.refresh_from_db()
        self.assertEqual(customer.workflow_state, Customer.WorkflowState.PAID)

        # Order status should be SUCCESS
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SUCCESS)

        # Outbound receipt message sent
        mock_client.messages.create.assert_called_once()
        sent_body = mock_client.messages.create.call_args[1].get("body", "")
        self.assertIn("Payment Confirmed", sent_body)



