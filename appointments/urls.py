from django.urls import path

from .views import BookAppointmentView, CancelAppointmentView, RescheduleAppointmentView

urlpatterns = [
    path("", BookAppointmentView.as_view(), name="appointment-book"),
    path("<int:appointment_id>/cancel/", CancelAppointmentView.as_view(), name="appointment-cancel"),
    path("<int:appointment_id>/reschedule/", RescheduleAppointmentView.as_view(), name="appointment-reschedule"),
]