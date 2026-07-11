from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Patient
from clinic.models import Doctor, WorkingHours

from .models import Appointment


class AppointmentTestBase(APITestCase):
    """Shared setup: one doctor with working hours, two patients."""

    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Achieng", specialty="General")
        self.target_date = timezone.localdate() + timedelta(days=7)
        WorkingHours.objects.create(
            doctor=self.doctor,
            day_of_week=self.target_date.weekday(),
            start_time="09:00",
            end_time="12:00",
        )

        self.user_a = User.objects.create_user(
            username="alice@example.com", email="alice@example.com", password="password123"
        )
        self.patient_a = Patient.objects.create(user=self.user_a, name="Alice")

        self.user_b = User.objects.create_user(
            username="bob@example.com", email="bob@example.com", password="password123"
        )
        self.patient_b = Patient.objects.create(user=self.user_b, name="Bob")

        self.slot_9am = timezone.make_aware(
            timezone.datetime.combine(self.target_date, timezone.datetime.min.time()).replace(hour=9)
        )

    def as_patient_a(self):
        self.client.force_authenticate(user=self.user_a)

    def as_patient_b(self):
        self.client.force_authenticate(user=self.user_b)


class BookAppointmentTests(AppointmentTestBase):
    def test_book_valid_slot_succeeds(self):
        self.as_patient_a()
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(Appointment.objects.first().patient, self.patient_a)

    def test_book_without_auth_returns_401(self):
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_book_nonexistent_doctor_returns_400(self):
        self.as_patient_a()
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": 9999, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_book_in_past_returns_400(self):
        self.as_patient_a()
        past = timezone.now() - timedelta(days=1)
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": past.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_book_within_one_hour_returns_400(self):
        self.as_patient_a()
        soon = timezone.now() + timedelta(minutes=30)
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": soon.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_book_outside_working_hours_returns_400(self):
        self.as_patient_a()
        outside = self.slot_9am.replace(hour=13)
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": outside.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_double_booking_same_slot_returns_400(self):
        self.as_patient_a()
        self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.as_patient_b()
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Appointment.objects.filter(status=Appointment.Status.BOOKED).count(), 1)


class CancelAppointmentTests(AppointmentTestBase):
    def setUp(self):
        super().setUp()
        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient_a,
            start_time=self.slot_9am,
            end_time=self.slot_9am + timedelta(minutes=30),
        )

    def test_cancel_own_appointment_succeeds(self):
        self.as_patient_a()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/cancel/",
            {"reason": "Feeling better"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)
        self.assertEqual(self.appointment.cancellation_reason, "Feeling better")

    def test_cancel_already_cancelled_returns_400(self):
        self.as_patient_a()
        self.client.patch(
            f"/api/appointments/{self.appointment.id}/cancel/", {"reason": "first"}, format="json"
        )

        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/cancel/", {"reason": "second"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_other_patients_appointment_returns_403(self):
        self.as_patient_b()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/cancel/", {"reason": "not mine"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.BOOKED)

    def test_cancelled_slot_becomes_bookable_again(self):
        self.as_patient_a()
        self.client.patch(
            f"/api/appointments/{self.appointment.id}/cancel/", {"reason": "changed plans"}, format="json"
        )

        self.as_patient_b()
        response = self.client.post(
            "/api/appointments/",
            {"doctor_id": self.doctor.id, "start_time": self.slot_9am.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class RescheduleAppointmentTests(AppointmentTestBase):
    def setUp(self):
        super().setUp()
        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient_a,
            start_time=self.slot_9am,
            end_time=self.slot_9am + timedelta(minutes=30),
        )
        self.new_slot = self.slot_9am + timedelta(minutes=30)  # 09:30

    def test_reschedule_own_appointment_succeeds(self):
        self.as_patient_a()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/reschedule/",
            {"start_time": self.new_slot.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_time, self.new_slot)

    def test_reschedule_other_patients_appointment_returns_403(self):
        self.as_patient_b()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/reschedule/",
            {"start_time": self.new_slot.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reschedule_cancelled_appointment_returns_400(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.cancellation_reason = "test"
        self.appointment.save()

        self.as_patient_a()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/reschedule/",
            {"start_time": self.new_slot.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reschedule_into_taken_slot_leaves_original_unchanged(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient_b,
            start_time=self.new_slot,
            end_time=self.new_slot + timedelta(minutes=30),
        )

        self.as_patient_a()
        response = self.client.patch(
            f"/api/appointments/{self.appointment.id}/reschedule/",
            {"start_time": self.new_slot.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_time, self.slot_9am)


class PatientAppointmentsListTests(AppointmentTestBase):
    def test_lists_only_own_upcoming_booked_appointments_sorted(self):
        later_slot = self.slot_9am + timedelta(minutes=60)
        Appointment.objects.create(
            doctor=self.doctor, patient=self.patient_a,
            start_time=later_slot, end_time=later_slot + timedelta(minutes=30),
        )
        Appointment.objects.create(
            doctor=self.doctor, patient=self.patient_a,
            start_time=self.slot_9am, end_time=self.slot_9am + timedelta(minutes=30),
        )
        cancelled_slot = self.slot_9am + timedelta(minutes=90)
        Appointment.objects.create(
            doctor=self.doctor, patient=self.patient_a,
            start_time=cancelled_slot, end_time=cancelled_slot + timedelta(minutes=30),
            status=Appointment.Status.CANCELLED, cancellation_reason="test",
        )
        # Someone else's appointment should never show up.
        Appointment.objects.create(
            doctor=self.doctor, patient=self.patient_b,
            start_time=self.slot_9am + timedelta(minutes=120),
            end_time=self.slot_9am + timedelta(minutes=150),
        )

        self.as_patient_a()
        response = self.client.get(f"/api/patients/{self.patient_a.id}/appointments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["start_time"], self.slot_9am.isoformat().replace("+00:00", "Z"))

    def test_cannot_view_another_patients_appointments(self):
        self.as_patient_a()
        response = self.client.get(f"/api/patients/{self.patient_b.id}/appointments/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)