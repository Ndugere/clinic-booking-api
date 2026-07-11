from django.urls import path

from .views import DoctorAvailabilityView

# Mounted under /api/doctors/ by the root URLconf.
urlpatterns = [
    path("<int:doctor_id>/availability/", DoctorAvailabilityView.as_view(), name="doctor-availability"),
]