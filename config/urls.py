from django.contrib import admin
from django.urls import include, path

from appointments.views import PatientAppointmentsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/patients/", include("accounts.urls")),
    path("api/patients/<int:patient_id>/appointments/", PatientAppointmentsView.as_view(), name="patient-appointments"),
    path("api/doctors/", include("clinic.urls")),
    path("api/appointments/", include("appointments.urls")),
]