"""
Customer and BusinessSetting models.
Tracks customer profiles, workflow state, and configurable business settings.
"""

from django.db import models


class Customer(models.Model):
    """
    Represents a customer/lead interacting via WhatsApp or web form.
    Tracks their current position in the sales workflow state machine.
    """

    class WorkflowState(models.TextChoices):
        NEW_LEAD = "NEW_LEAD", "New Lead"
        AWAITING_REPLY = "AWAITING_REPLY", "Awaiting Reply"
        INTERESTED = "INTERESTED", "Interested"
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        PAID = "PAID", "Paid"
        ESCALATED = "ESCALATED", "Escalated"

    class Source(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        WEB_FORM = "WEB_FORM", "Web Form"

    # Contact info
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="E.164 format, e.g. +2348012345678",
    )
    name = models.CharField(max_length=120, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)

    # Workflow state machine
    workflow_state = models.CharField(
        max_length=20,
        choices=WorkflowState.choices,
        default=WorkflowState.NEW_LEAD,
        db_index=True,
    )

    # Human takeover
    human_takeover = models.BooleanField(default=False, db_index=True)
    takeover_by = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text="Admin username who took over the conversation",
    )

    # Follow-up tracking
    follow_up_count = models.PositiveSmallIntegerField(default=0)
    last_message_at = models.DateTimeField(blank=True, null=True)

    # Source & metadata
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.WHATSAPP,
    )
    extra_data = models.JSONField(blank=True, null=True, help_text="Flexible metadata")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["last_message_at"], name="idx_last_message_at"),
        ]

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_number}) — {self.workflow_state}"


class BusinessSetting(models.Model):
    """
    Key-value store for configurable business settings.
    Editable from the admin dashboard.
    """

    setting_key = models.CharField(max_length=80, unique=True)
    setting_value = models.TextField()
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_settings"
        ordering = ["setting_key"]

    def __str__(self):
        return f"{self.setting_key}: {self.setting_value[:50]}"

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Retrieve a setting value by key, with an optional default."""
        try:
            return cls.objects.get(setting_key=key).setting_value
        except cls.DoesNotExist:
            return default
