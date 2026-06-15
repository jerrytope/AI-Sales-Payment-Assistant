"""
Order model — tracks payment transactions via Paystack.
"""

from django.db import models
from apps.customers.models import Customer


class Order(models.Model):
    """
    Represents a payment transaction for a customer.
    Tracks Paystack references, amounts, status, and reminder counts.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        ABANDONED = "ABANDONED", "Abandoned"

    # Relationship
    customer = models.ForeignKey(
        Customer,
        on_delete=models.RESTRICT,
        related_name="orders",
        db_index=True,
    )

    # Amount (stored in kobo — smallest currency unit)
    amount_kobo = models.PositiveIntegerField(
        help_text="Amount in kobo (e.g., 500000 = ₦5,000)",
    )
    currency = models.CharField(max_length=3, default="NGN")

    # Paystack references
    paystack_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    paystack_access_code = models.CharField(max_length=100, blank=True, null=True)
    payment_url = models.URLField(max_length=512, blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Paystack webhook payload (raw, for audit trail)
    gateway_response = models.JSONField(blank=True, null=True)

    # Reminder tracking
    reminder_count = models.PositiveSmallIntegerField(default=0)
    last_reminder_at = models.DateTimeField(blank=True, null=True)

    # Payment timestamp
    paid_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        amount_naira = self.amount_kobo / 100
        return f"Order #{self.id} — ₦{amount_naira:,.2f} ({self.status})"

    @property
    def amount_naira(self):
        """Return the amount in Naira (for display purposes)."""
        return self.amount_kobo / 100
