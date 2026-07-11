from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Patient


class PatientRegistrationTests(APITestCase):
    """Tests for POST /api/patients/register/."""

    def setUp(self):
        self.register_url = "/api/patients/register/"
        self.valid_payload = {
            "name": "Jane Wanjiru",
            "email": "jane@example.com",
            "phone_number": "0700000001",
            "password": "supersecret123",
        }

    def test_register_creates_user_and_patient(self):
        response = self.client.post(self.register_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)

        patient = Patient.objects.first()
        self.assertEqual(patient.name, "Jane Wanjiru")
        self.assertEqual(patient.user.email, "jane@example.com")

    def test_register_rejects_duplicate_email(self):
        self.client.post(self.register_url, self.valid_payload, format="json")

        response = self.client.post(self.register_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        # Only the first registration should have gone through.
        self.assertEqual(Patient.objects.count(), 1)

    def test_register_rejects_short_password(self):
        payload = {**self.valid_payload, "password": "short"}

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 0)


class PatientLoginTests(APITestCase):
    """Tests for POST /api/patients/login/."""

    def setUp(self):
        self.login_url = "/api/patients/login/"
        self.register_url = "/api/patients/register/"
        self.credentials = {"email": "jane@example.com", "password": "supersecret123"}
        self.client.post(
            self.register_url,
            {"name": "Jane Wanjiru", **self.credentials},
            format="json",
        )

    def test_login_with_correct_credentials_returns_token(self):
        response = self.client.post(self.login_url, self.credentials, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_with_wrong_password_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {"email": "jane@example.com", "password": "wrongpassword"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_unregistered_email_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {"email": "ghost@example.com", "password": "whatever123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)