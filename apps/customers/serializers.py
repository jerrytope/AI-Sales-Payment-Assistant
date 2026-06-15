"""
Customer serializers for DRF API.
"""

from rest_framework import serializers
from apps.conversations.serializers import MessageSerializer
from .models import Customer, BusinessSetting


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer list views."""

    class Meta:
        model = Customer
        fields = [
            "id",
            "phone_number",
            "name",
            "email",
            "workflow_state",
            "human_takeover",
            "follow_up_count",
            "source",
            "last_message_at",
            "created_at",
            "updated_at",
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Full serializer for customer detail views, including message history."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "phone_number",
            "name",
            "email",
            "workflow_state",
            "human_takeover",
            "takeover_by",
            "follow_up_count",
            "last_message_at",
            "source",
            "extra_data",
            "created_at",
            "updated_at",
            "messages",
        ]


class BusinessSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSetting
        fields = ["id", "setting_key", "setting_value", "description", "updated_at"]
        read_only_fields = ["id", "updated_at"]
