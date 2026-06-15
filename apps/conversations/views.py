"""
WhatsApp webhook view — handles inbound Twilio messages.
Full implementation will be completed in Phase 2/3.
"""

import logging
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from django.utils import timezone
from apps.customers.models import Customer
from apps.messaging.decorators import validate_twilio_signature
from .models import Message

logger = logging.getLogger(__name__)


@method_decorator(validate_twilio_signature, name="dispatch")
class WhatsAppWebhookView(APIView):
    """
    Receives inbound WhatsApp messages from Twilio.
    Parses the payload, upserts the customer, saves the message,
    and passes it through the AI + workflow pipeline.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhook"

    def post(self, request):
        data = request.data
        phone = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "").strip()
        media = data.get("MediaUrl0")
        twilio_sid = data.get("MessageSid")

        if not phone or not body:
            return Response({"error": "Missing required fields"}, status=400)

        logger.info(f"Inbound message from {phone}: {body[:50]}")

        # 1. Upsert customer
        customer, created = Customer.objects.get_or_create(
            phone_number=phone,
            defaults={"workflow_state": "NEW_LEAD", "source": "WHATSAPP"},
        )
        if created:
            logger.info(f"New customer created: {phone}")

        # Update last_message_at
        customer.last_message_at = timezone.now()
        customer.save(update_fields=["last_message_at", "updated_at"])

        # 2. Save inbound message
        message = Message.objects.create(
            customer=customer,
            body=body,
            media_url=media,
            direction="INBOUND",
            sender_type="USER",
            twilio_sid=twilio_sid,
        )

        # 3. Skip AI if human has taken over
        if customer.human_takeover:
            logger.info(f"Skipping AI for {phone} — human takeover active")
            return Response(status=200)

        # 4. AI intent classification + workflow engine
        from apps.ai_engine.intent_classifier import classify_intent
        from apps.workflows.state_machine import WorkflowEngine

        # Get history (excluding the current inbound message we just saved)
        history = list(
            customer.messages.exclude(id=message.id)
            .order_by("-created_at")[:10]
            .values("body", "sender_type")
        )

        try:
            result = classify_intent(body, history)
            message.detected_intent = result.get("intent", Message.Intent.UNKNOWN)
            message.intent_confidence = result.get("confidence", 0.0)
            message.save(update_fields=["detected_intent", "intent_confidence"])

            engine = WorkflowEngine(customer)
            engine.process(intent=result["intent"], suggested_reply=result["reply"])
        except Exception as e:
            logger.error(f"Error processing message {message.id} through AI/Workflow: {e}")
            # Graceful fallback response on processing failure
            from apps.messaging.twilio_client import TwilioWhatsAppClient
            twilio = TwilioWhatsAppClient()
            fallback_msg = "Thank you for your message! We're checking that for you and will get back to you shortly."
            try:
                sid = twilio.send_message(customer.phone_number, fallback_msg)
                Message.objects.create(
                    customer=customer,
                    body=fallback_msg,
                    direction=Message.Direction.OUTBOUND,
                    sender_type=Message.SenderType.BOT,
                    twilio_sid=sid,
                )
            except Exception as twilio_err:
                logger.error(f"Failed to send fallback message: {twilio_err}")

        return Response(status=200)

