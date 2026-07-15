from django.core.management.base import BaseCommand

from clinic.models import Doctor, WorkingHours

DEMO_DOCTORS = [
    {
        "name": "Dr. Amina Achieng",
        "specialty": "General Practice",
        "hours": [(0, "09:00", "17:00"), (1, "09:00", "17:00"), (2, "09:00", "17:00"),
                   (3, "09:00", "17:00"), (4, "09:00", "17:00")],
    },
    {
        "name": "Dr. James Otieno",
        "specialty": "Dentistry",
        "hours": [(0, "08:00", "14:00"), (2, "08:00", "14:00"), (4, "08:00", "14:00")],
    },
    {
        "name": "Dr. Grace Wambui",
        "specialty": "Pediatrics",
        "hours": [(1, "09:00", "13:00"), (2, "09:00", "13:00"), (3, "09:00", "13:00"),
                   (4, "09:00", "13:00"), (5, "09:00", "13:00")],
    },
    {
        "name": "Dr. Peter Mwangi",
        "specialty": "Dermatology",
        "hours": [(0, "10:00", "16:00"), (1, "10:00", "16:00"), (2, "10:00", "16:00"),
                   (3, "10:00", "16:00")],
    },
    {
        "name": "Dr. Sarah Njeri",
        "specialty": "Gynecology",
        "hours": [(0, "09:00", "15:00"), (1, "09:00", "15:00"), (3, "09:00", "15:00"),
                   (4, "09:00", "15:00")],
    },
]


class Command(BaseCommand):
    """Seeds 5 demo doctors with realistic, varied working hours.

    Idempotent: matches on doctor name, so running this multiple times
    (e.g. on every deploy, or repeatedly by hand locally) never creates
    duplicates. Safe to include in a build command or CI step.
    """

    help = "Creates demo doctors and working hours if they don't already exist."

    def handle(self, *args, **options):
        for entry in DEMO_DOCTORS:
            doctor, created = Doctor.objects.get_or_create(
                name=entry["name"], defaults={"specialty": entry["specialty"]}
            )
            if not created:
                self.stdout.write(f"Doctor '{doctor.name}' already exists -- skipping.")
                continue

            for day_of_week, start, end in entry["hours"]:
                WorkingHours.objects.get_or_create(
                    doctor=doctor,
                    day_of_week=day_of_week,
                    defaults={"start_time": start, "end_time": end},
                )
            self.stdout.write(self.style.SUCCESS(f"Created doctor '{doctor.name}' with working hours."))