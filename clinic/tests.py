from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Patient
from appointments.models import Appointment
from .models import Doctor, WorkingHours


class DoctorAvailabilityTests(APITestCase):
    """Tests for GET /api/doctors/{id}/availability/."""

    def setUp(self):
        self.doctor = Doctor.objects.create(name="Dr. Otieno", specialty="Dentistry")
        # Pick a date 7 days out so "past date" tests never accidentally collide with it.
        self.target_date = timezone.localdate() + timedelta(days=7)
        WorkingHours.objects.create(
            doctor=self.doctor,
            day_of_week=self.target_date.weekday(),
            start_time="09:00",
            end_time="11:00",
        )
        self.url = f"/api/doctors/{self.doctor.id}/availability/"

    def test_returns_all_slots_when_nothing_booked(self):
        response = self.client.get(self.url, {"date": self.target_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 09:00-11:00 in 30-minute increments = 4 slots
        self.assertEqual(len(response.data["available_slots"]), 4)

    def test_booked_slot_is_excluded_from_availability(self):
        user = User.objects.create_user(username="p@example.com", email="p@example.com", password="pass12345")
        patient = Patient.objects.create(user=user, name="Test Patient")
        tz = timezone.get_current_timezone()
        slot = timezone.make_aware(datetime.combine(self.target_date, datetime.min.time()).replace(hour=9, minute=30), tz)
        Appointment.objects.create(
            doctor=self.doctor, patient=patient, start_time=slot, end_time=slot + timedelta(minutes=30)
        )

        response = self.client.get(self.url, {"date": self.target_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["available_slots"]), 3)
        self.assertNotIn(slot.isoformat(), response.data["available_slots"])

    def test_past_date_returns_400(self):
        past_date = timezone.localdate() - timedelta(days=1)

        response = self.client.get(self.url, {"date": past_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_doctor_returns_404(self):
        response = self.client.get("/api/doctors/9999/availability/", {"date": self.target_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_day_doctor_does_not_work_returns_empty_list(self):
        non_working_date = self.target_date + timedelta(days=1)

        response = self.client.get(self.url, {"date": non_working_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["available_slots"], [])