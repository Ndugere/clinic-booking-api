from datetime import datetime, timedelta

from django.utils import timezone

SLOT_MINUTES = 30


def get_available_slots(doctor, date, exclude_appointment_id=None):
    """Compute available 30-minute slot start-times for a doctor on a date.

    Returns a list of timezone-aware datetimes. Empty list if the doctor
    has no WorkingHours configured for that day of week, or if every
    slot that day is already booked.

    exclude_appointment_id: when checking a slot on behalf of a
    reschedule, the appointment being rescheduled should not count as
    "blocking" itself.

    This function is also reused by appointments.validators to check a
    requested start_time against the same slot grid used here, so
    booking and availability can never disagree with each other.
    """
    from appointments.models import Appointment

    working_hours = doctor.working_hours.filter(day_of_week=date.weekday()).first()
    if not working_hours:
        return []

    tz = timezone.get_current_timezone()
    current = timezone.make_aware(datetime.combine(date, working_hours.start_time), tz)
    end = timezone.make_aware(datetime.combine(date, working_hours.end_time), tz)

    all_slots = []
    while current + timedelta(minutes=SLOT_MINUTES) <= end:
        all_slots.append(current)
        current += timedelta(minutes=SLOT_MINUTES)

    booked_qs = Appointment.objects.filter(
        doctor=doctor,
        status=Appointment.Status.BOOKED,
        start_time__date=date,
    )
    if exclude_appointment_id is not None:
        booked_qs = booked_qs.exclude(id=exclude_appointment_id)

    booked_times = set(booked_qs.values_list("start_time", flat=True))

    return [slot for slot in all_slots if slot not in booked_times]