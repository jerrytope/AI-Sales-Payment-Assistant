"""
Message serializers for DRF API.
"""

from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "customer",
            "body",
            "media_url",
            "direction",
            "sender_type",
            "detected_intent",
            "intent_confidence",
            "twilio_sid",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
