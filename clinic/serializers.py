from django.utils import timezone
from rest_framework import serializers


class AvailabilityQuerySerializer(serializers.Serializer):
    """Validates the ``?date=`` query param for the availability endpoint."""

    date = serializers.DateField()

    def validate_date(self, value):
        """Reject dates before today; past days have no bookable slots."""
        if value < timezone.localdate():
            raise serializers.ValidationError("Cannot check availability for a past date.")
        return value


class AvailabilityResponseSerializer(serializers.Serializer):
    """Response shape for GET /doctors/{id}/availability/ (documentation only)."""

    doctor_id = serializers.IntegerField()
    doctor_name = serializers.CharField()
    date = serializers.DateField()
    available_slots = serializers.ListField(child=serializers.DateTimeField())