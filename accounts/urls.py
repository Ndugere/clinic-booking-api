from django.urls import path

from .views import LoginView, RegisterView

# Mounted under /api/patients/ by the root URLconf.
urlpatterns = [
    path("register/", RegisterView.as_view(), name="patient-register"),
    path("login/", LoginView.as_view(), name="patient-login"),
]