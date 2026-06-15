"""
Message model — stores all inbound and outbound WhatsApp messages
with AI-detected intent classification.
"""

from django.db import models
from apps.customers.models import Customer


class Message(models.Model):
    """
    A single message in a customer conversation.
    Tracks direction (inbound/outbound), sender type, and AI intent classification.
    """

    class Direction(models.TextChoices):
        INBOUND = "INBOUND", "Inbound"
        OUTBOUND = "OUTBOUND", "Outbound"

    class SenderType(models.TextChoices):
        USER = "USER", "User"
        BOT = "BOT", "Bot"
        ADMIN = "ADMIN", "Admin"

    class Intent(models.TextChoices):
        GREETING = "GREETING", "Greeting"
        PRODUCT_INQUIRY = "PRODUCT_INQUIRY", "Product Inquiry"
        BUYING_INTENT = "BUYING_INTENT", "Buying Intent"
        OBJECTION = "OBJECTION", "Objection"
        SUPPORT_OR_HUMAN = "SUPPORT_OR_HUMAN", "Support / Human"
        UNKNOWN = "UNKNOWN", "Unknown"

    # Relationship
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )

    # Message content
    body = models.TextField()
    media_url = models.URLField(max_length=512, blank=True, null=True)

    # Direction & sender
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        db_index=True,
    )
    sender_type = models.CharField(
        max_length=10,
        choices=SenderType.choices,
    )

    # AI classification
    detected_intent = models.CharField(
        max_length=20,
        choices=Intent.choices,
        blank=True,
        null=True,
        db_index=True,
    )
    intent_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Confidence score from 0.000 to 1.000",
    )

    # Twilio tracking
    twilio_sid = models.CharField(max_length=64, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"], name="idx_customer_created"),
        ]

    def __str__(self):
        return f"[{self.direction}] {self.sender_type} → {self.body[:50]}"
