from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.Serializer):
    """Response shape for a registered patient (documentation + register response)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()


class TokenSerializer(serializers.Serializer):
    """Response shape for a successful login."""

    token = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    """Validates registration input and creates the underlying ``User`` + ``Patient``.

    ``email`` doubles as the login username (see ``validate_email``), so its
    uniqueness is enforced here at the User layer rather than on ``Patient``.
    """

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        """Reject the email if it's already registered, case-insensitively."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A patient with this email is already registered.")
        return value

    def create(self, validated_data):
        """Create the auth ``User`` (email as username) and its linked ``Patient``."""
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        patient = Patient.objects.create(
            user=user,
            name=validated_data["name"],
            phone_number=validated_data.get("phone_number", ""),
        )
        return patient


class LoginSerializer(serializers.Serializer):
    """Validates email/password credentials against Django's auth backend."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate the given credentials, attaching the resolved ``user``.

        Uses a single generic error message on failure so the response
        doesn't reveal whether the email exists in the system.
        """
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs