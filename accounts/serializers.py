from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Patient


class RegisterSerializer(serializers.Serializer):
    """Validates registration input and creates a User + Patient together.

    Email uniqueness is enforced here (at the serializer/User layer) since
    Django's built-in User.email field is NOT unique by default. This is
    intentionally the single source of truth for identity -- Patient does
    not duplicate an email field (see accounts.models.Patient docstring).
    """

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A patient with this email is already registered.")
        return value

    def create(self, validated_data):
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
    """Validates credentials and resolves them to a Django User via authenticate().

    Note: Django's authenticate() checks against `username`, so we log in
    with `username=email` under the hood -- consistent with how we created
    the user at registration time.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs