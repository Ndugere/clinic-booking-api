from django.db import models

from accounts.models import Patient
from clinic.models import Doctor


class Appointment(models.Model):
    """A booked (or cancelled) 30-minute slot for a patient with a doctor.

    Concurrency safety: the conditional UniqueConstraint below is the
    real defense against double-booking, not the application-level
    validation in the serializer/view. Two simultaneous requests for the
    same (doctor, start_time) will race at the application layer, but
    the database will reject the second INSERT/UPDATE outright. The
    condition=Q(status=BOOKED) clause matters: without it, a cancelled
    appointment would permanently block that slot from ever being
    rebooked, since the old (cancelled) row would still collide.

    No separate Slot table: available slots are computed dynamically
    from WorkingHours minus existing BOOKED appointments (see
    appointments.availability). This keeps the schema simple and avoids
    a sync problem between "slot exists" and "appointment exists", at
    the cost of a bit more computation per availability request -- an
    acceptable trade-off at this clinic's scale.
    """

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"

    doctor = models.ForeignKey(Doctor, related_name="appointments", on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, related_name="appointments", on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.BOOKED
    )
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_time"],
                condition=models.Q(status="booked"),
                name="unique_booked_slot_per_doctor",
            )
        ]

    def __str__(self):
        return f"{self.patient.name} with {self.doctor.name} @ {self.start_time} ({self.status})"