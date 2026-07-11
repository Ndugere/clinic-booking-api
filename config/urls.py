from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from appointments.views import PatientAppointmentsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/patients/", include("accounts.urls")),
    path("api/patients/<int:patient_id>/appointments/", PatientAppointmentsView.as_view(), name="patient-appointments"),
    path("api/doctors/", include("clinic.urls")),
    path("api/appointments/", include("appointments.urls")),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]