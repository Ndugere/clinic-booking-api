from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, PatientSerializer, RegisterSerializer, TokenSerializer


class RegisterView(APIView):
    """Public endpoint for creating a new patient account."""

    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: PatientSerializer})
    def post(self, request):
        """Validate registration data, create the patient, and return its public fields."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            {"id": patient.id, "name": patient.name, "email": patient.user.email},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Public endpoint for exchanging email/password credentials for an auth token."""

    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: TokenSerializer})
    def post(self, request):
        """Authenticate the request and return (or create) the patient's DRF token."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_200_OK)