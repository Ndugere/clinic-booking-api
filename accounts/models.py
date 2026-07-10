from django.contrib.auth.models import User
from django.db import models


class Patient(models.Model):
    """A patient who can book appointments.

    Wraps Django's built-in ``User`` model rather than reinventing
    password storage/hashing. Identity for login is the user's email
    (see accounts.serializers for registration, which enforces email
    uniqueness at the User layer -- not duplicated here).

    Phone number is kept as an optional contact field only; it is NOT
    used for authentication and is not unique, since a clinic may
    reasonably want to store it without it doubling as a login key.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient")
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name