from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .availability import get_available_slots
from .models import Doctor
from .serializers import AvailabilityQuerySerializer


class DoctorAvailabilityView(APIView):
    """GET /api/doctors/{doctor_id}/availability/?date=YYYY-MM-DD

    Public endpoint -- overrides the project-wide IsAuthenticated
    default, since a patient should be able to see what's free before
    they've registered or logged in.
    """

    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
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