from datetime import timedelta

from rest_framework import serializers

from clinic.models import Doctor

from .models import Appointment
from .validators import validate_slot

SLOT_MINUTES = 30


class AppointmentSerializer(serializers.ModelSerializer):
    """Read-only representation used in all endpoint responses."""

    doctor_name = serializers.CharField(source="doctor.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "patient",
            "start_time",
            "end_time",
            "status",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = fields


class BookAppointmentSerializer(serializers.Serializer):
    """POST /api/appointments/ -- patient is taken from the authenticated
    request, never from the request body (closes the gap where one
    patient could book/cancel on behalf of another by tampering with a
    patient_id field).
    """

    doctor_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()

    def validate(self, attrs):
        try:
            doctor = Doctor.objects.get(id=attrs["doctor_id"])
        except Doctor.DoesNotExist:
            raise serializers.ValidationError({"doctor_id": "Doctor not found."})

        validate_slot(doctor, attrs["start_time"])

        attrs["doctor"] = doctor
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        patient = request.user.patient
        start_time = validated_data["start_time"]

        return Appointment.objects.create(
            doctor=validated_data["doctor"],
            patient=patient,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=SLOT_MINUTES),
        )


class CancelAppointmentSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, allow_blank=False)


class RescheduleAppointmentSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
