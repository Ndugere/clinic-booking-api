from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer


class RegisterView(APIView):
    """POST /api/patients/register/ -- creates a Patient account.

    permission_classes overrides the project-wide default of
    IsAuthenticated (set in settings.py) -- registration must be
    reachable by someone who doesn't have a token yet.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            {
                "id": patient.id,
                "name": patient.name,
                "email": patient.user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/patients/login/ -- exchanges email+password for a token.

    Reuses (or creates) a single token per user via get_or_create, so a
    patient always gets the same token back on repeated logins rather
    than accumulating a new one every time.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_200_OK)