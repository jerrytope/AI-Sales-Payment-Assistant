"""
Twilio WhatsApp client — sends messages via the Twilio API.
Full implementation in Phase 2 (T-2.1).
"""

import logging
from twilio.rest import Client
from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioWhatsAppClient:
    """Client for sending WhatsApp messages via Twilio."""

    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self.from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"

    def send_message(self, to_phone: str, body: str, media_url: str = None) -> str:
        """
        Send a WhatsApp message to a customer.

        Args:
            to_phone: Recipient phone number (E.164 format, e.g. +2348012345678)
            body: Message text
            media_url: Optional URL of media attachment

        Returns:
            Twilio message SID
        """
        kwargs = {
            "from_": self.from_number,
            "to": f"whatsapp:{to_phone}",
            "body": body,
        }
        if media_url:
            kwargs["media_url"] = [media_url]

        try:
            message = self.client.messages.create(**kwargs)
            logger.info(f"WhatsApp sent to {to_phone} — SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {to_phone}: {e}")
            raise
