from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from clinic.availability import get_available_slots

MIN_BOOKING_LEAD = timedelta(hours=1)


def validate_slot(doctor, start_time, exclude_appointment_id=None):
    now = timezone.now()

    if start_time < now:
        raise serializers.ValidationError("Cannot book an appointment in the past.")

    if start_time < now + MIN_BOOKING_LEAD:
        raise serializers.ValidationError(
            "Appointments must be booked at least 1 hour in advance."
        )

    available_slots = get_available_slots(
        doctor, start_time.date(), exclude_appointment_id=exclude_appointment_id
    )
    if start_time not in available_slots:
        raise serializers.ValidationError(
            "That slot is not available. It may be outside the doctor's "
            "working hours, not aligned to a 30-minute slot, or already booked."
        )