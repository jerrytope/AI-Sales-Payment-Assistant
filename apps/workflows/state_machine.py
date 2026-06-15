"""
Workflow State Machine — the core sales automation engine.
Manages state transitions and triggers actions (messages, payment links, follow-ups).
Full implementation in Phase 3 (T-3.1).
"""

import uuid
import logging
from django.utils import timezone
from apps.customers.models import Customer, BusinessSetting
from apps.conversations.models import Message
from apps.messaging.twilio_client import TwilioWhatsAppClient
from apps.messaging.templates import (
    welcome_message,
    payment_link_message,
    escalation_message,
)
from apps.payments.paystack import PaystackClient
from apps.payments.models import Order

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    State-driven workflow engine.
    Accepts a customer record and an intent, then executes the appropriate
    state transition and side-effects (messages, payment links, scheduled tasks).
    """

    TRANSITIONS = {
        "NEW_LEAD": ["AWAITING_REPLY", "INTERESTED", "PENDING_PAYMENT", "ESCALATED"],
        "AWAITING_REPLY": ["INTERESTED", "PENDING_PAYMENT", "ESCALATED", "AWAITING_REPLY"],
        "INTERESTED": ["PENDING_PAYMENT", "ESCALATED"],
        "PENDING_PAYMENT": ["PAID", "ESCALATED"],
        "PAID": [],
        "ESCALATED": [],
    }

    def __init__(self, customer: Customer):
        self.customer = customer
        self.twilio = TwilioWhatsAppClient()
        self.paystack = PaystackClient()

    def transition_to(self, new_state: str) -> bool:
        """Validate and execute a state transition."""
        allowed = self.TRANSITIONS.get(self.customer.workflow_state, [])
        if new_state in allowed:
            old_state = self.customer.workflow_state
            self.customer.workflow_state = new_state
            self.customer.save(update_fields=["workflow_state", "updated_at"])
            logger.info(
                f"Customer {self.customer.phone_number}: {old_state} -> {new_state}"
            )
            return True
        logger.warning(
            f"Invalid transition for {self.customer.phone_number}: "
            f"{self.customer.workflow_state} -> {new_state}"
        )
        return False

    def process(self, intent: str, suggested_reply: str):
        """
        Main dispatcher — evaluates the intent and executes the workflow.

        Args:
            intent: Classified intent from the AI engine
            suggested_reply: AI-generated reply text
        """
        c = self.customer

        if intent == "BUYING_INTENT":
            self._handle_buying_intent(suggested_reply)

        elif intent == "SUPPORT_OR_HUMAN":
            self._escalate()

        elif intent == "GREETING" and c.workflow_state == "NEW_LEAD":
            self._send_introduction(suggested_reply)
            self.transition_to("AWAITING_REPLY")
            # Schedule follow-up (Phase 3)
            from apps.workflows.tasks import send_follow_up

            send_follow_up.apply_async(args=[c.id], countdown=6 * 3600)

        else:
            # Default: send the AI reply
            sid = self.twilio.send_message(c.phone_number, suggested_reply)
            self._save_outbound(suggested_reply, sid)
            c.last_message_at = timezone.now()
            c.save(update_fields=["last_message_at"])

    def _handle_buying_intent(self, suggested_reply: str):
        """Generate a Paystack payment link and send it to the customer."""
        c = self.customer

        ref = f"SALE-{c.id}-{uuid.uuid4().hex[:8].upper()}"
        amount_kobo = self._get_product_price_kobo()

        try:
            result = self.paystack.initialize_transaction(
                email=c.email or f"{c.phone_number}@placeholder.com",
                amount=amount_kobo,
                reference=ref,
                metadata={"customer_phone": c.phone_number, "customer_id": c.id},
            )
        except Exception as e:
            logger.error(f"Paystack error for {c.phone_number}: {e}")
            sid = self.twilio.send_message(
                c.phone_number,
                "Sorry, we're having trouble generating your payment link. Please try again shortly!",
            )
            self._save_outbound("Payment link generation failed — apology sent.", sid)
            return

        order = Order.objects.create(
            customer=c,
            amount_kobo=amount_kobo,
            paystack_reference=ref,
            paystack_access_code=result.get("access_code"),
            payment_url=result.get("authorization_url"),
            status="PENDING",
        )

        msg = payment_link_message(order.payment_url)
        sid = self.twilio.send_message(c.phone_number, msg)
        self._save_outbound(msg, sid)
        self.transition_to("PENDING_PAYMENT")

        # Schedule payment reminders (Phase 3)
        from apps.workflows.tasks import send_payment_reminder

        for i in range(1, 4):
            send_payment_reminder.apply_async(
                args=[order.id], countdown=i * 24 * 3600
            )

    def _escalate(self):
        """Flag the customer for human takeover."""
        c = self.customer
        c.human_takeover = True
        c.workflow_state = "ESCALATED"
        c.save(update_fields=["human_takeover", "workflow_state", "updated_at"])

        msg = escalation_message()
        sid = self.twilio.send_message(c.phone_number, msg)
        self._save_outbound(msg, sid)
        logger.info(f"Customer {c.phone_number} escalated to human agent")

    def _send_introduction(self, suggested_reply: str):
        """Send a welcome message to a new lead."""
        business_name = BusinessSetting.get("business_name", "our store")
        msg = welcome_message(business_name)
        sid = self.twilio.send_message(self.customer.phone_number, msg)
        self._save_outbound(msg, sid)

    def _get_product_price_kobo(self) -> int:
        """
        Get the product price from business settings.
        TODO: Replace with dynamic product lookup from catalog.
        """
        return 500_000  # Default ₦5,000 in kobo

    def _save_outbound(self, body: str, sid: str):
        """Save an outbound bot message to the database."""
        Message.objects.create(
            customer=self.customer,
            body=body,
            direction="OUTBOUND",
            sender_type="BOT",
            twilio_sid=sid,
        )
