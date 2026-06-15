"""
Celery tasks for automated follow-ups and payment reminders.
Full implementation in Phase 3 (T-3.3).
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_follow_up(self, customer_id: int):
    """
    Send a follow-up message to a customer who hasn't replied.
    Scheduled with a 6-hour countdown after the last interaction.
    Caps at 3 follow-ups.
    """
    from apps.customers.models import Customer
    from apps.messaging.twilio_client import TwilioWhatsAppClient
    from apps.messaging.templates import follow_up_messages
    from apps.conversations.models import Message

    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        logger.warning(f"Follow-up aborted: Customer {customer_id} not found")
        return

    # Abort if state has changed (customer responded or was escalated)
    if customer.workflow_state not in ("AWAITING_REPLY", "NEW_LEAD"):
        logger.info(f"Follow-up skipped for {customer.phone_number}: state is {customer.workflow_state}")
        return
    if customer.human_takeover:
        logger.info(f"Follow-up skipped for {customer.phone_number}: human takeover active")
        return
    if customer.follow_up_count >= 3:
        logger.info(f"Follow-up limit reached for {customer.phone_number}")
        return

    twilio = TwilioWhatsAppClient()
    messages = follow_up_messages()
    msg = messages[min(customer.follow_up_count, len(messages) - 1)]

    try:
        sid = twilio.send_message(customer.phone_number, msg)
    except Exception as e:
        logger.error(f"Follow-up send failed for {customer.phone_number}: {e}")
        backoff = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=backoff)

    Message.objects.create(
        customer=customer,
        body=msg,
        direction="OUTBOUND",
        sender_type="BOT",
        twilio_sid=sid,
    )

    customer.follow_up_count += 1
    customer.save(update_fields=["follow_up_count", "updated_at"])
    logger.info(f"Follow-up #{customer.follow_up_count} sent to {customer.phone_number}")

    # Schedule next follow-up if under the cap
    if customer.follow_up_count < 3:
        send_follow_up.apply_async(args=[customer_id], countdown=6 * 3600)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_reminder(self, order_id: int):
    """
    Send a payment reminder to a customer with a pending order.
    Scheduled at 24h, 48h, and 72h after payment link generation.
    """
    from apps.payments.models import Order
    from apps.messaging.twilio_client import TwilioWhatsAppClient
    from apps.messaging.templates import payment_reminder_message
    from apps.conversations.models import Message

    try:
        order = Order.objects.select_related("customer").get(id=order_id)
    except Order.DoesNotExist:
        logger.warning(f"Payment reminder aborted: Order {order_id} not found")
        return

    # Abort if already paid or failed
    if order.status != "PENDING":
        logger.info(f"Payment reminder skipped for Order {order_id}: status is {order.status}")
        return

    customer = order.customer
    amount_naira = order.amount_kobo / 100
    msg = payment_reminder_message(amount_naira, order.payment_url)

    twilio = TwilioWhatsAppClient()
    try:
        sid = twilio.send_message(customer.phone_number, msg)
    except Exception as e:
        logger.error(f"Payment reminder send failed for {customer.phone_number}: {e}")
        backoff = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=backoff)

    Message.objects.create(
        customer=customer,
        body=msg,
        direction="OUTBOUND",
        sender_type="BOT",
        twilio_sid=sid,
    )

    order.reminder_count += 1
    order.last_reminder_at = timezone.now()
    order.save(update_fields=["reminder_count", "last_reminder_at", "updated_at"])
    logger.info(f"Payment reminder #{order.reminder_count} sent for Order {order_id}")
