from django.urls import path

from .views import DoctorAvailabilityView

urlpatterns = [
    path("<int:doctor_id>/availability/", DoctorAvailabilityView.as_view(), name="doctor-availability"),
]