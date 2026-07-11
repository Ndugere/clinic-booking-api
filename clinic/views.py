from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .availability import get_available_slots
from .models import Doctor
from .serializers import AvailabilityQuerySerializer, AvailabilityResponseSerializer


class DoctorAvailabilityView(APIView):
    """Public endpoint listing a doctor's free slots for a given date."""

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Date to check availability for, format YYYY-MM-DD. Must not be in the past.",
            )
        ],
        responses={200: AvailabilityResponseSerializer},
    )
    def get(self, request, doctor_id):
        """Return the doctor's available slot start-times for ``?date=``."""
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        target_date = query.validated_data["date"]

        slots = get_available_slots(doctor, target_date)

        return Response(
            {
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "date": target_date,
                "available_slots": [slot.isoformat() for slot in slots],
            },
            status=status.HTTP_200_OK,
        )