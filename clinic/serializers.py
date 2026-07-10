from django.utils import timezone
from rest_framework import serializers


class AvailabilityQuerySerializer(serializers.Serializer):
    """Validates the ?date= query param for the availability endpoint.

    Rejects past dates with a 400 here, rather than silently returning
    an empty slot list -- an empty list would be indistinguishable from
    "doctor is fully booked" or "doctor doesn't work that day", which
    are legitimately different situations for a frontend to display.
    """

    date = serializers.DateField()

    def validate_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Cannot check availability for a past date.")
        return value