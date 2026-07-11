from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Read-friendly listing of patients in the Django admin."""

    list_display = ("id", "name", "phone_number", "user")