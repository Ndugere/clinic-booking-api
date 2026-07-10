from django.db import models


class Doctor(models.Model):
    """A doctor who sees patients at the clinic.

    Deliberately minimal: no auth/login fields here. Doctor records are
    managed by clinic staff via Django Admin, not through a public API
    endpoint -- the spec only requires a patient-facing booking API.
    """

    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class WorkingHours(models.Model):
    """A doctor's working hours for a single day of the week.

    Modeled per-day (rather than one fixed shift for every day) because
    "set working hours" in the brief is ambiguous, and real clinics
    commonly have different hours on different days (e.g. shorter hours
    on Saturday). This is a documented assumption -- see README.
    """

    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        Doctor, related_name="working_hours", on_delete=models.CASCADE
    )
    day_of_week = models.IntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "day_of_week"],
                name="unique_working_hours_per_doctor_per_day",
            )
        ]
        ordering = ["day_of_week"]

    def __str__(self):
        return f"{self.doctor.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"