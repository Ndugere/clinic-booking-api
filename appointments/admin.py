from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin listing of appointments, filterable by status and doctor."""

    list_display = ("id", "doctor", "patient", "start_time", "status")
    list_filter = ("status", "doctor")