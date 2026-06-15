"""
Paystack API client — handles transaction initialization and webhook verification.
Full implementation in Phase 2 (T-2.4).
"""

import hmac
import hashlib
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackClient:
    """Client for interacting with the Paystack API."""

    def __init__(self):
        self.secret = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self, email: str, amount: int, reference: str, metadata: dict = None
    ) -> dict:
        """
        Initialize a Paystack transaction.

        Args:
            email: Customer email address
            amount: Amount in kobo (e.g., 500000 = ₦5,000)
            reference: Unique transaction reference
            metadata: Optional metadata dict

        Returns:
            dict with authorization_url, access_code, reference
        """
        payload = {
            "email": email,
            "amount": amount,
            "reference": reference,
            "callback_url": settings.PAYSTACK_CALLBACK_URL,
            "metadata": metadata or {},
        }
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"]

    def verify_transaction(self, reference: str) -> dict:
        """Verify a transaction by its reference."""
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"]

    @staticmethod
    def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA512 signature from Paystack webhook."""
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
        computed = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, signature)
