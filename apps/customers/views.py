import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import Customer, BusinessSetting
from .serializers import CustomerListSerializer, CustomerDetailSerializer, BusinessSettingSerializer
from apps.ai_engine.intent_classifier import classify_intent


logger = logging.getLogger(__name__)


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for listing and retrieving customers."""

    queryset = Customer.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerListSerializer

    @action(detail=True, methods=["post"])
    def takeover(self, request, pk=None):
        """Toggle human takeover for a customer conversation."""
        customer = self.get_object()
        customer.human_takeover = not customer.human_takeover
        customer.takeover_by = request.user.username if customer.human_takeover else None
        customer.save(update_fields=["human_takeover", "takeover_by", "updated_at"])
        return Response(
            {
                "human_takeover": customer.human_takeover,
                "takeover_by": customer.takeover_by,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """Send a manual WhatsApp message to a customer as an Admin."""
        customer = self.get_object()
        body = request.data.get("body", "").strip()

        if not body:
            return Response({"error": "Message body is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Enforce human takeover if sending manual messages
        if not customer.human_takeover:
            customer.human_takeover = True
            customer.takeover_by = request.user.username if request.user.is_authenticated else "admin"
            customer.save(update_fields=["human_takeover", "takeover_by", "updated_at"])

        # 2. Send via Twilio
        from apps.messaging.twilio_client import TwilioWhatsAppClient
        twilio = TwilioWhatsAppClient()

        try:
            sid = twilio.send_message(customer.phone_number, body)
        except Exception as e:
            logger.error(f"Admin message failed to send to {customer.phone_number}: {e}")
            return Response({"error": f"Twilio API error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        # 3. Save to database as OUTBOUND, sender_type=ADMIN
        from apps.conversations.models import Message
        msg = Message.objects.create(
            customer=customer,
            body=body,
            direction=Message.Direction.OUTBOUND,
            sender_type=Message.SenderType.ADMIN,
            twilio_sid=sid,
        )

        # 4. Update last_message_at
        customer.last_message_at = timezone.now()
        customer.save(update_fields=["last_message_at", "updated_at"])

        # Return serialized message
        from apps.conversations.serializers import MessageSerializer
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)



class BusinessSettingViewSet(viewsets.ModelViewSet):
    """API viewset for managing business settings."""

    queryset = BusinessSetting.objects.all()
    serializer_class = BusinessSettingSerializer
    lookup_field = "setting_key"


class LeadCaptureView(APIView):
    """
    Public API endpoint to capture leads from the landing page.
    Saves lead details, records the message, and triggers the AI workflow.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get("name", "").strip()
        phone = request.data.get("phone", "").strip()
        email = request.data.get("email", "").strip()
        message_body = request.data.get("message", "").strip()

        if not phone or not name:
            return Response({"error": "Name and phone number are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize phone numbers to E.164 (Nigeria format by default)
        formatted_phone = phone
        if not formatted_phone.startswith("+"):
            clean_phone = formatted_phone.lstrip("0")
            if len(clean_phone) == 10:  # e.g., 8012345678 -> +2348012345678
                formatted_phone = f"+234{clean_phone}"
            else:
                formatted_phone = f"+{clean_phone}"

        # 1. Upsert customer record
        customer, created = Customer.objects.get_or_create(
            phone_number=formatted_phone,
            defaults={
                "name": name,
                "email": email or None,
                "workflow_state": Customer.WorkflowState.NEW_LEAD,
                "source": Customer.Source.WEB_FORM,
            },
        )
        if not created:
            if name and not customer.name:
                customer.name = name
            if email and not customer.email:
                customer.email = email
            customer.last_message_at = timezone.now()
            customer.save(update_fields=["name", "email", "last_message_at", "updated_at"])
        else:
            customer.last_message_at = timezone.now()
            customer.save(update_fields=["last_message_at"])

        # 2. Save inbound message
        body_content = message_body or "Interested in products (via Web Lead Form)"
        from apps.conversations.models import Message
        message = Message.objects.create(
            customer=customer,
            body=body_content,
            direction=Message.Direction.INBOUND,
            sender_type=Message.SenderType.USER,
        )

        # 3. Skip AI/Workflow if takeover is active
        if customer.human_takeover:
            logger.info(f"Skipping AI for web lead {customer.phone_number} — human takeover active")
            return Response({"status": "success", "message": "Lead captured; takeover active"}, status=status.HTTP_201_CREATED)

        # 4. Trigger workflow engine
        from apps.workflows.state_machine import WorkflowEngine

        # Get history (excluding current message)
        history = list(
            customer.messages.exclude(id=message.id)
            .order_by("-created_at")[:10]
            .values("body", "sender_type")
        )

        try:
            result = classify_intent(body_content, history)
            message.detected_intent = result.get("intent", Message.Intent.UNKNOWN)
            message.intent_confidence = result.get("confidence", 0.0)
            message.save(update_fields=["detected_intent", "intent_confidence"])

            engine = WorkflowEngine(customer)
            engine.process(intent=result["intent"], suggested_reply=result["reply"])
        except Exception as e:
            logger.error(f"Error processing web lead {customer.phone_number} through AI: {e}")
            
            # Send fallback welcome message
            from apps.messaging.twilio_client import TwilioWhatsAppClient
            from apps.messaging.templates import welcome_message
            business_name = BusinessSetting.get("business_name", "our store")
            fallback_reply = welcome_message(business_name)
            try:
                twilio = TwilioWhatsAppClient()
                sid = twilio.send_message(customer.phone_number, fallback_reply)
                Message.objects.create(
                    customer=customer,
                    body=fallback_reply,
                    direction=Message.Direction.OUTBOUND,
                    sender_type=Message.SenderType.BOT,
                    twilio_sid=sid
                )
            except Exception as twilio_err:
                logger.error(f"Failed to send web lead fallback WhatsApp: {twilio_err}")

        return Response({"status": "success", "customer_id": customer.id}, status=status.HTTP_201_CREATED)
