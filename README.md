The patient identity used for booking, cancelling, rescheduling, and
   viewing appointment history always comes from this token — there is
   no `patient_id` field anywhere in a request body, by design.

`GET /doctors/{id}/availability` is the one public endpoint — a patient
should be able to see what's free before they've registered.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/patients/register/` | none | Create a patient account |
| POST | `/api/patients/login/` | none | Exchange credentials for a token |
| GET | `/api/doctors/{id}/availability/?date=YYYY-MM-DD` | none | List free 30-minute slots for a doctor on a date |
| POST | `/api/appointments/` | token | Book a slot (`doctor_id`, `start_time`) |
| PATCH | `/api/appointments/{id}/cancel/` | token, owner only | Cancel with a `reason` |
| PATCH | `/api/appointments/{id}/reschedule/` | token, owner only | Move to a new `start_time` |
| GET | `/api/patients/{id}/appointments/` | token, owner only | Upcoming booked appointments, sorted by date |

### Example: booking an appointment

```bash
curl -X POST https://<deployed-url>/api/appointments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <your_token>" \
  -d '{"doctor_id": 1, "start_time": "2026-07-20T09:00:00Z"}'
```

**Validation enforced on every booking and reschedule** (each returns
`400` with a specific message on failure):
- Slot must fall within the doctor's working hours
- Slot must not be in the past
- Slot must be at least 1 hour from now
- Slot must not already be booked — also enforced at the database
  level, which returns `409` if two requests genuinely race for the
  same slot

---

## Running Locally

```bash
git clone https://github.com/Ndugere/clinic-booking-api.git
cd clinic-booking-api

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # needed for /admin, to add doctors + working hours
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/admin`, log in, and add a `Doctor`
with their `WorkingHours` (there's an inline form for this right on
the Doctor page). From there the API is usable as described above.

### Running the tests

```bash
python manage.py test
```

I have 28 tests across the three apps, covering: registration and
login (both success and failure paths), availability computation
(including the past-date, non-working-day, and already-booked-slot
edge cases), and the full booking/cancel/reschedule lifecycle,
including ownership enforcement and the reschedule-into-a-taken-slot
scenario.

---

## CI/CD

_TBD — completed as part of Section 3._

- Public URL:
- Branch that triggers deployment:
- What the pipeline does:

---

## Section 4: AI Reflection

_(See below or `AI_REFLECTION.md`.)_

1. **What did I use AI for across the four sections?**
2. **One example where an AI suggestion improved my work — what did I prompt it with?**
3. **One example where AI output was wrong or incomplete — how did I catch it?**
4. **Two decisions I made without AI — why did I trust my own judgment there?**