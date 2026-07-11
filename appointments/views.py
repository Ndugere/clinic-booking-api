from datetime import timedelta

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    BookAppointmentSerializer,
    CancelAppointmentSerializer,
    RescheduleAppointmentSerializer,
)
from .validators import validate_slot

SLOT_MINUTES = 30


class BookAppointmentView(APIView):
    """POST /api/appointments/

    Validates doctor existence, working hours, past-date, and the
    1-hour minimum lead time via BookAppointmentSerializer/validate_slot
    (fast, friendly errors). The actual double-booking guarantee comes
    from the database's conditional UniqueConstraint on Appointment --
    if two requests race past the validate_slot check simultaneously,
    the second INSERT raises IntegrityError, which we translate into a
    409 Conflict here.
    """

    @extend_schema(request=BookAppointmentSerializer, responses={201: AppointmentSerializer})
    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                appointment = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "That slot was just booked by someone else. Please choose another."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class CancelAppointmentView(APIView):
    """PATCH /api/appointments/{id}/cancel/

    Only the patient who owns the appointment may cancel it. Cancelling
    an already-cancelled appointment is rejected with a 400, per spec.
    """

    @extend_schema(request=CancelAppointmentSerializer, responses={200: AppointmentSerializer})
    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)

        if appointment.patient.user_id != request.user.id:
            return Response(
                {"detail": "You do not have permission to modify this appointment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status == Appointment.Status.CANCELLED:
            return Response(
                {"detail": "This appointment is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = serializer.validated_data["reason"]
        appointment.save()

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)


class RescheduleAppointmentView(APIView):
    """PATCH /api/appointments/{id}/reschedule/

    Updates the SAME appointment row's start_time/end_time in place
    (rather than deleting + recreating), inside transaction.atomic().
    This is what makes "free the old slot" and "claim the new slot" a
    single atomic operation: if the new slot turns out to be taken (by
    another request that won the race), the UPDATE violates the unique
    constraint, IntegrityError is raised, the transaction rolls back,
    and the original appointment is left completely untouched -- the
    patient never loses their original slot on a failed reschedule.
    """

    @extend_schema(request=RescheduleAppointmentSerializer, responses={200: AppointmentSerializer})
    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)

        if appointment.patient.user_id != request.user.id:
            return Response(
                {"detail": "You do not have permission to modify this appointment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status == Appointment.Status.CANCELLED:
            return Response(
                {"detail": "Cannot reschedule a cancelled appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RescheduleAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_start = serializer.validated_data["start_time"]

        validate_slot(appointment.doctor, new_start, exclude_appointment_id=appointment.id)

        try:
            with transaction.atomic():
                appointment.start_time = new_start
                appointment.end_time = new_start + timedelta(minutes=SLOT_MINUTES)
                appointment.save()
        except IntegrityError:
            return Response(
                {
                    "detail": "That slot was just booked by someone else. "
                    "Your original appointment is unchanged."
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)


class PatientAppointmentsView(APIView):
    """GET /api/patients/{patient_id}/appointments/

    Upcoming (BOOKED, start_time in the future) appointments only,
    sorted by date. Although the patient_id is in the URL, only the
    authenticated patient matching that id may access it -- prevents
    enumerating other patients' appointment history.
    """

    @extend_schema(responses={200: AppointmentSerializer(many=True)})
    def get(self, request, patient_id):
        if request.user.patient.id != patient_id:
            return Response(
                {"detail": "You do not have permission to view this patient's appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        appointments = Appointment.objects.filter(
            patient_id=patient_id,
            status=Appointment.Status.BOOKED,
            start_time__gte=timezone.now(),
        ).order_by("start_time")

        return Response(AppointmentSerializer(appointments, many=True).data, status=status.HTTP_200_OK)