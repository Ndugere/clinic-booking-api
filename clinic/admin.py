from django.contrib import admin

from .models import Doctor, WorkingHours


class WorkingHoursInline(admin.TabularInline):
    """Lets staff add/edit a doctor's weekly working hours on the Doctor admin page."""

    model = WorkingHours
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Admin listing for doctors, with their working hours editable inline."""

    list_display = ("id", "name", "specialty")
    inlines = [WorkingHoursInline]