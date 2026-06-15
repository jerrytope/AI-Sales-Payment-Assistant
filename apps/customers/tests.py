from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from apps.customers.models import Customer, BusinessSetting
from apps.conversations.models import Message
from apps.payments.models import Order


class ApiEndpointsTestCase(APITestCase):
    def setUp(self):
        # Create standard admin user for DRF auth
        self.username = "api_admin"
        self.password = "securepass123"
        self.user = User.objects.create_superuser(
            username=self.username,
            email="admin@example.com",
            password=self.password
        )
        self.client.force_authenticate(user=self.user)

        # Create dummy customer data
        self.customer = Customer.objects.create(
            phone_number="+2348012345678",
            name="Temi Tope",
            email="temi@example.com",
            workflow_state=Customer.WorkflowState.NEW_LEAD,
            human_takeover=False
        )

        # Create dummy message
        self.message = Message.objects.create(
            customer=self.customer,
            body="Hello from customer",
            direction=Message.Direction.INBOUND,
            sender_type=Message.SenderType.USER
        )

        # Create dummy order
        self.order = Order.objects.create(
            customer=self.customer,
            amount_kobo=150000,
            paystack_reference="REF-TEST-999",
            status=Order.Status.PENDING
        )

        # Update or create settings (since database migrations might seed default rows)
        self.setting, _ = BusinessSetting.objects.update_or_create(
            setting_key="business_name",
            defaults={
                "setting_value": "Temi Stores",
                "description": "The name of the business"
            }
        )

    def test_customer_list_authenticated(self):
        """Authenticated users can retrieve the customer list."""
        url = reverse("customer-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify pagination and values
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Temi Tope")

    def test_customer_detail_authenticated(self):
        """Authenticated users can retrieve customer detail, which includes messages."""
        url = reverse("customer-detail", kwargs={"pk": self.customer.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Temi Tope")
        self.assertIn("messages", response.data)
        self.assertEqual(len(response.data["messages"]), 1)
        self.assertEqual(response.data["messages"][0]["body"], "Hello from customer")

    def test_customer_takeover_toggle(self):
        """POST /api/customers/{id}/takeover/ toggles the human takeover flag."""
        url = reverse("customer-takeover", kwargs={"pk": self.customer.id})
        
        # First toggle: should turn takeover ON
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["human_takeover"])
        self.assertEqual(response.data["takeover_by"], self.username)

        self.customer.refresh_from_db()
        self.assertTrue(self.customer.human_takeover)
        self.assertEqual(self.customer.takeover_by, self.username)

        # Second toggle: should turn takeover OFF
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["human_takeover"])
        self.assertIsNone(response.data["takeover_by"])

        self.customer.refresh_from_db()
        self.assertFalse(self.customer.human_takeover)
        self.assertIsNone(self.customer.takeover_by)

    @patch("apps.messaging.twilio_client.Client")
    def test_customer_send_message_success(self, mock_twilio_client_class):
        """POST /api/customers/{id}/send-message/ sends message and forces human takeover."""
        # Setup mock client
        mock_client = MagicMock()
        mock_twilio_client_class.return_value = mock_client
        mock_message = MagicMock()
        mock_message.sid = "SMadmin123"
        mock_client.messages.create.return_value = mock_message

        url = reverse("customer-send-message", kwargs={"pk": self.customer.id})
        payload = {"body": "This is an admin manual response."}

        # Verify initial state
        self.assertFalse(self.customer.human_takeover)

        # Action
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "This is an admin manual response.")
        self.assertEqual(response.data["direction"], "OUTBOUND")
        self.assertEqual(response.data["sender_type"], "ADMIN")

        # Database assertions
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.human_takeover)
        self.assertEqual(self.customer.takeover_by, self.username)
        self.assertIsNotNone(self.customer.last_message_at)

        # Verify a Message object was created
        admin_messages = Message.objects.filter(
            customer=self.customer, 
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.ADMIN
        )
        self.assertEqual(admin_messages.count(), 1)
        self.assertEqual(admin_messages.first().body, "This is an admin manual response.")
        self.assertEqual(admin_messages.first().twilio_sid, "SMadmin123")

    def test_customer_send_message_empty_body(self):
        """POST /api/customers/{id}/send-message/ returns 400 for empty message body."""
        url = reverse("customer-send-message", kwargs={"pk": self.customer.id})
        response = self.client.post(url, {"body": "  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("apps.messaging.twilio_client.Client")
    def test_customer_send_message_twilio_failure(self, mock_twilio_client_class):
        """POST /api/customers/{id}/send-message/ returns 502 if Twilio API raises an exception."""
        # Setup mock client to throw exception
        mock_client = MagicMock()
        mock_twilio_client_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Twilio down")

        url = reverse("customer-send-message", kwargs={"pk": self.customer.id})
        response = self.client.post(url, {"body": "Test message"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    def test_order_list_authenticated(self):
        """Authenticated users can retrieve the order payment ledger."""
        url = reverse("order-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"][0]["paystack_reference"], "REF-TEST-999")
        self.assertEqual(response.data["results"][0]["customer_name"], "Temi Tope")
        self.assertEqual(response.data["results"][0]["amount_naira"], 1500.0)

    def test_business_settings_endpoints(self):
        """Tests managing settings via BusinessSettingViewSet."""
        # Test List
        list_url = reverse("businesssetting-list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        setting_keys = [item["setting_key"] for item in response.data["results"]]
        self.assertIn("business_name", setting_keys)

        # Test Update
        detail_url = reverse("businesssetting-detail", kwargs={"setting_key": "business_name"})
        update_data = {"setting_key": "business_name", "setting_value": "Acme Inc."}
        response = self.client.put(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["setting_value"], "Acme Inc.")

        self.setting.refresh_from_db()
        self.assertEqual(self.setting.setting_value, "Acme Inc.")

    @patch("apps.messaging.twilio_client.Client")
    @patch("apps.customers.views.classify_intent")
    def test_lead_capture_success(self, mock_classify, mock_twilio_client_class):
        """POST /api/leads/ creates customer, normalization, saves inbound msg and runs AI workflow."""
        # Setup mock intent
        mock_classify.return_value = {
            "intent": "GREETING",
            "confidence": 0.98,
            "reply": "Welcome to our page!"
        }
        # Setup mock twilio client
        mock_client = MagicMock()
        mock_twilio_client_class.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.sid = "SMmocklead123"
        mock_client.messages.create.return_value = mock_msg

        # Unauthenticate client since leads submission is public
        self.client.force_authenticate(user=None)

        url = reverse("lead-capture")
        payload = {
            "name": "Jane Doe",
            "phone": "08123456789",
            "email": "jane@example.com",
            "message": "Hi, I am looking to get pricing."
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("customer_id", response.data)

        # Check DB State: E.164 phone normalization and Lead Source
        customer = Customer.objects.get(phone_number="+2348123456789")
        self.assertEqual(customer.name, "Jane Doe")
        self.assertEqual(customer.email, "jane@example.com")
        self.assertEqual(customer.source, Customer.Source.WEB_FORM)
        # Verify workflow transitioned state (GREETING transitions NEW_LEAD -> AWAITING_REPLY)
        self.assertEqual(customer.workflow_state, Customer.WorkflowState.AWAITING_REPLY)

        # Assert messages saved
        inbound_msg = Message.objects.filter(customer=customer, direction=Message.Direction.INBOUND).first()
        self.assertIsNotNone(inbound_msg)
        self.assertEqual(inbound_msg.body, "Hi, I am looking to get pricing.")
        self.assertEqual(inbound_msg.detected_intent, "GREETING")

        outbound_msg = Message.objects.filter(customer=customer, direction=Message.Direction.OUTBOUND).first()
        self.assertIsNotNone(outbound_msg)
        self.assertEqual(outbound_msg.sender_type, Message.SenderType.BOT)

    def test_lead_capture_missing_params(self):
        """POST /api/leads/ returns 400 if name or phone is missing."""
        self.client.force_authenticate(user=None)
        url = reverse("lead-capture")
        
        # Missing phone
        response = self.client.post(url, {"name": "Test User"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing name
        response = self.client.post(url, {"phone": "08123456789"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.customers.views.classify_intent")
    def test_lead_capture_takeover_skips_ai(self, mock_classify):
        """POST /api/leads/ skips AI processing if customer is already flagged for human takeover."""
        # Pre-create customer with human takeover active
        cust = Customer.objects.create(
            phone_number="+2348123456789",
            name="John Takeover",
            human_takeover=True
        )

        self.client.force_authenticate(user=None)
        url = reverse("lead-capture")
        payload = {
            "name": "John Takeover",
            "phone": "08123456789",
            "message": "Need help from real human"
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify Gemini classifier was NOT called
        mock_classify.assert_not_called()

