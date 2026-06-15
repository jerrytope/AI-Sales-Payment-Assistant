import json
import logging
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from apps.customers.models import Customer
from apps.messaging.twilio_client import TwilioWhatsAppClient
from apps.messaging.templates import payment_success_message
from .models import Order
from .paystack import PaystackClient
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)


class PaystackWebhookView(APIView):
    """
    Receives Paystack webhook events (e.g., charge.success).
    Verifies the HMAC signature and updates order status.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhook"

    def post(self, request):
        signature = request.headers.get("x-paystack-signature", "")
        payload_bytes = request.body

        # 1. Verify signature
        if not PaystackClient.verify_webhook_signature(payload_bytes, signature):
            logger.warning("Invalid Paystack signature received")
            return Response({"error": "Invalid signature"}, status=401)

        # 2. Parse payload
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse Paystack webhook body: {e}")
            return Response({"error": "Invalid JSON"}, status=400)

        event = payload.get("event")
        logger.info(f"Paystack webhook event received: {event}")

        if event == "charge.success":
            data = payload.get("data", {})
            ref = data.get("reference")
            if not ref:
                return Response({"error": "Missing reference"}, status=400)

            # 3. Lookup Order
            try:
                order = Order.objects.select_related("customer").get(paystack_reference=ref)
            except Order.DoesNotExist:
                logger.warning(f"Order with reference {ref} not found")
                return Response({"status": "ignored", "message": "Order not found"}, status=200)

            # 4. Idempotency check
            if order.status == Order.Status.SUCCESS:
                return Response({"status": "ignored", "message": "Order already processed"}, status=200)

            # 5. Update Order status
            order.status = Order.Status.SUCCESS
            order.paid_at = timezone.now()
            order.gateway_response = data
            order.save(update_fields=["status", "paid_at", "gateway_response", "updated_at"])

            # 6. Update Customer workflow_state
            customer = order.customer
            customer.workflow_state = Customer.WorkflowState.PAID
            customer.save(update_fields=["workflow_state", "updated_at"])

            # 7. Send receipt message
            amount_naira = order.amount_naira
            receipt_msg = payment_success_message(customer.name, amount_naira, ref)

            try:
                twilio = TwilioWhatsAppClient()
                twilio.send_message(customer.phone_number, receipt_msg)
            except Exception as e:
                logger.error(f"Failed to send payment confirmation to {customer.phone_number}: {e}")

        return Response(status=200)



class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for listing and retrieving orders (payment ledger)."""

    queryset = Order.objects.select_related("customer").all()
    serializer_class = OrderSerializer
