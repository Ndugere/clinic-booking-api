# Clinic Booking API

A REST API for a small clinic (5 doctors) that lets patients check a
doctor's availability, book a 30-minute appointment slot, cancel a
booking, or reschedule it — built with Django REST Framework.

---

## Live Application

- **Public URL:** https://clinic-booking-api-cnnv.onrender.com
- **Interactive API docs (Swagger):** https://clinic-booking-api-cnnv.onrender.com/api/docs/
- **Interactive API docs (Redoc):** https://clinic-booking-api-cnnv.onrender.com/api/redoc/
- **Admin panel:** https://clinic-booking-api-cnnv.onrender.com/admin/
- **Repository:** https://github.com/Ndugere/clinic-booking-api

---

## How to Test This

The fastest way is the interactive Swagger docs — open
https://clinic-booking-api-cnnv.onrender.com/api/docs/, use
`POST /api/patients/register/` and `POST /api/patients/login/` to get
a token, click **Authorize** at the top and paste `Token <your_token>`,
then every other endpoint on the page becomes callable directly from
the browser.

For a scripted walkthrough hitting the exact endpoints in the brief,
against the live deployment, in order:

**1. Register a patient**
```bash
curl -X POST https://clinic-booking-api-cnnv.onrender.com/api/patients/register/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Patient", "email": "test@example.com", "password": "testpass123"}'
```

**2. Log in to get a token**
```bash
curl -X POST https://clinic-booking-api-cnnv.onrender.com/api/patients/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```
Copy the `token` from the response for the steps below.

**3. Check a doctor's availability** (`GET /doctors/{id}/availability`)
```bash
curl "https://clinic-booking-api-cnnv.onrender.com/api/doctors/3/availability/?date=2026-07-20"
```
Doctor `3` is Dr. Amina Achieng (General Practice, Mon–Fri 09:00–17:00)
— July 20, 2026 is a Monday, so this returns a full day of open slots.
The other 4 pre-seeded doctors are ids `4`–`7`, each with different
specialties and working days (see "Seeding demo data" below).

**4. Book one of those slots** (`POST /appointments`)
```bash
curl -X POST https://clinic-booking-api-cnnv.onrender.com/api/appointments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token PASTE_TOKEN_HERE" \
  -d '{"doctor_id": 3, "start_time": "2026-07-20T09:00:00Z"}'
```
Note the returned `id` — needed below. Re-running this exact command a
second time demonstrates the "already taken" validation (`400`);
changing `start_time` to something in the past, or to within the next
hour, demonstrates the other two validation rules.

**5. Cancel it** (`PATCH /appointments/{id}/cancel`)
```bash
curl -X PATCH https://clinic-booking-api-cnnv.onrender.com/api/appointments/APPOINTMENT_ID/cancel/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token PASTE_TOKEN_HERE" \
  -d '{"reason": "Testing cancellation"}'
```
Running this a second time demonstrates the "already cancelled"
validation (`400`). Re-checking step 3's availability afterward
confirms the slot is bookable again.

**6. Reschedule** (`PATCH /appointments/{id}/reschedule`)
Book a fresh slot (repeat step 4 with a different `start_time`), then:
```bash
curl -X PATCH https://clinic-booking-api-cnnv.onrender.com/api/appointments/NEW_APPOINTMENT_ID/reschedule/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token PASTE_TOKEN_HERE" \
  -d '{"start_time": "2026-07-20T10:00:00Z"}'
```

**Bonus — upcoming appointments** (`GET /patients/{id}/appointments`)
```bash
curl https://clinic-booking-api-cnnv.onrender.com/api/patients/PATIENT_ID/appointments/ \
  -H "Authorization: Token PASTE_TOKEN_HERE"
```
`PATIENT_ID` was returned in step 1's response.

### Why doctors are already pre-seeded

Render's free tier doesn't provide shell access, so there's no
interactive way to run `createsuperuser` or manually seed data via
Django Admin directly on the deployed instance. I solved this with two
small, idempotent management commands
(`accounts/management/commands/ensure_superuser.py` and
`clinic/management/commands/seed_demo_data.py`) wired into the Render
build step — they create an admin login and 5 demo doctors with
realistic, varied working hours on first deploy, and safely do nothing
on every deploy after that (they check for existing records before
creating anything, so re-running them is harmless). This means the
live app is always populated and testable without needing my admin
credentials or any manual setup on your end.

---

## How I approached this

Before writing a single line of code, I treated Section 1 as an actual
design exercise rather than a formality — I wanted to know what the
models were, where the ambiguity in the brief actually was, and what
I'd be trading off before I committed to a schema. That thinking is
captured below, and it directly shaped how I split the codebase, how I
handled auth, and where I chose not to build something.

## Project structure: why three apps, not one

I split the codebase into three Django apps — `accounts`, `clinic`,
and `appointments` — instead of putting everything in a single
`models.py` and `views.py`. This wasn't just to satisfy the "structure
your code sensibly" constraint in the brief; I actually think it's the
right shape for this domain, for a few concrete reasons:

- **Each app maps to one bounded concern**, not just one model.
  `accounts` owns patient identity and auth. `clinic` owns doctors and
  their working hours — the relatively static, admin-managed side of
  the system. `appointments` owns the actual booking lifecycle — the
  part that changes constantly and has all the concurrency-sensitive
  logic. When I'm working on booking validation, I never need to think
  about how patient registration works, and vice versa — the
  boundaries match how I actually reason about the problem.
- **It matches how the brief itself is structured.** The scenario
  describes doctors/hours, patients booking, and the booking lifecycle
  as three fairly separate concerns. Mirroring that in the codebase
  means the code organization and the problem statement stay in sync,
  which makes it easier for someone reading this repo cold to find
  where a given piece of behavior lives.
- **It scales better if this clinic actually grows**, which the brief
  explicitly says is the goal. If I ever needed to add, say, a
  `billing` app or a `notifications` app, they'd slot in as siblings
  rather than requiring me to untangle a single large app first.
- **Each app owns its own tests**, so I can run `python manage.py test
  accounts` in isolation while iterating on auth, without waiting on
  the full suite. That mattered more than I expected once I got to the
  appointments app, since those tests take the longest (concurrency
  and transaction-heavy tests aren't free).

The one place this created a genuine cross-app dependency is
`appointments` needing to import `clinic.models.Doctor` and
`clinic.availability.get_available_slots` — I decided that's fine and
not a smell, because the dependency direction is one-way
(`appointments` depends on `clinic`, never the reverse), which keeps
the app graph a clean tree rather than a cycle.

## Models — what I built and why

### `Doctor` and `WorkingHours` (`clinic` app)

```python
class Doctor(models.Model):
    name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255, blank=True)


class WorkingHours(models.Model):
    doctor = models.ForeignKey(Doctor, related_name="working_hours", on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["doctor", "day_of_week"], name="unique_working_hours_per_doctor_per_day")
        ]
```

I kept `Doctor` deliberately thin — there's no public endpoint to
create one. The brief only asks for a patient-facing booking API, so I
manage doctors entirely through Django Admin, where I also add their
`WorkingHours` inline on the same form.

`WorkingHours` is one row **per day of the week**, not a single fixed
shift applied to every day. "Set working hours" was ambiguous in the
brief, and I chose the per-day model because it's how clinics actually
run — a doctor might work Monday–Friday but only half a day Saturday —
and it costs almost nothing extra in the schema to support that.

### `Patient` (`accounts` app)

```python
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient")
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True)
```

I wrapped Django's built-in `User` rather than writing my own
password/auth handling — no reason to reinvent battle-tested hashing.
I went back and forth on phone number vs. email as the login
identifier and landed on **email**, mainly because it's what `User`
already supports natively, and it's the cleaner path if I ever add
verification or password-reset later (Django has first-class tooling
for email flows; phone/OTP verification needs a paid SMS provider even
in production). `phone_number` is still on the model, but purely as an
optional contact field — it has no role in authentication.

### `Appointment` (`appointments` app)

```python
class Appointment(models.Model):
    doctor = models.ForeignKey(Doctor, related_name="appointments", on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, related_name="appointments", on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_time"],
                condition=models.Q(status="booked"),
                name="unique_booked_slot_per_doctor",
            )
        ]
```

I deliberately did **not** create a separate `Slot` table. Available
slots are computed on demand from `WorkingHours` minus existing
`booked` appointments, rather than pre-materializing a row per slot.
That keeps the schema smaller and avoids a sync problem — a `Slot`
table would always need to agree with the `Appointment` table about
what's taken, and I'd rather not carry that risk at this clinic's
scale. The trade-off is a little more computation per availability
request, which I think is the right side of that trade-off to be on
for 5 doctors — I'd reconsider it if this needed to handle a lot more
traffic (see Growth Considerations).

## The core design decision: preventing double-booking

This is the part I spent the most time on, because "mostly correct"
isn't good enough here.

My first instinct was to check availability in application code before
inserting a new appointment. But that has a real race window — two
requests can both check, both see the slot as free, and both insert.
So I moved the actual guarantee down to the database: a **conditional
unique constraint** on `(doctor, start_time)`, scoped to
`status="booked"`. Two simultaneous booking attempts for the same slot
will both pass my application-level check, but only one `INSERT` can
succeed — the database rejects the second one outright, and I catch
that as `IntegrityError` and turn it into a `409 Conflict`.

The `condition=Q(status="booked")` clause matters more than it looks:
without it, a *cancelled* appointment's row would still count toward
uniqueness and would permanently block that slot from ever being
rebooked. I verified this exact behavior with a direct test: book a
slot, confirm a second booking for the same slot fails, cancel the
first, confirm the slot becomes bookable again.

My application-level check (`appointments/validators.py`) still runs
first, before the database is ever touched — not because it prevents
the race, but because it produces a fast, specific, friendly error
message in the normal case ("outside working hours," "already
booked," "too soon"), instead of every rejected booking waiting on a
database round-trip for a generic error. The constraint is the actual
safety net; the validator is the user-facing layer on top of it.

## Reschedule: atomicity and "what if I lose my slot"

Rescheduling updates the **same** `Appointment` row's `start_time` and
`end_time` in place — not delete-old, create-new. That's what makes
"free the old slot" and "claim the new slot" a single atomic unit
rather than two operations that could partially fail. The whole thing
is wrapped in `transaction.atomic()`.

If a patient tries to reschedule into a slot that gets taken by
someone else in the moment between my application-level check and the
actual write, the `UPDATE` violates the same unique constraint
described above. `IntegrityError` is raised, the transaction rolls
back completely, and the original appointment is left exactly as it
was — a failed reschedule never costs the patient their original slot.
I have a test asserting this directly: attempt a reschedule into an
already-taken slot, then assert the appointment's `start_time` is
still the original value afterward.

## Doctor cancelling an entire day (design only, not implemented)

This came up as a design question in the brief, not as one of the
four required endpoints or the two bonus items, so I chose not to
build it — but "not built" shouldn't mean "not thought through."

I'd add a `WorkingHoursException` model:

```python
class WorkingHoursException(models.Model):
    doctor = models.ForeignKey(Doctor, related_name="exceptions", on_delete=models.CASCADE)
    date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
```

`get_available_slots(doctor, date)` would check this table before
doing anything else and return `[]` immediately if a row exists for
that `(doctor, date)` — an early return, not a rewrite of the function
I already built.

The real reason I stopped here: marking a day off doesn't retroactively
touch `Appointment` rows already booked for it, since I keep
availability computation and existing bookings deliberately decoupled.
So blocking new bookings that day does nothing on its own for patients
who already have a slot booked — and that has no clean default. Either
auto-cancel those appointments (simple, but silently cancelling
something a patient is relying on isn't something I'd ship without
notifying them), or flag them for staff to follow up on manually
(safer — a human decides whether to call the patient). Both need a
notification mechanism that doesn't exist anywhere in this project,
which is the actual reason I didn't build this — it's not one model
and one endpoint, it's an unresolved decision about patient
communication I didn't want to answer badly under time pressure. If I
were shipping this, I'd start with the manual-flag option, since it
fails safe.

## Design decisions and assumptions, in one place

| Question | My decision |
|---|---|
| What is a "slot"? | A fixed grid, computed dynamically from working hours minus booked appointments — not its own table. If a doctor's working window doesn't divide evenly into 30-minute chunks (e.g. a 40-minute shift), the leftover remainder is never offered — I verified this directly rather than assuming it. |
| Timezones | All datetimes stored and compared as timezone-aware (UTC by default). I assumed a single clinic in a single timezone. |
| Working hours change → existing bookings | Not retroactively invalidated — a real limitation, not an oversight. A production system would need a reconciliation step to flag now-invalid bookings, which I haven't built. |
| Authentication — who can book on behalf of whom | Patients self-register (email + password) and book only for themselves. The `patient` on every appointment always comes from the authenticated token, never from a field in the request body — this closes the gap where one patient could act on another's behalf by tampering with an id in the JSON. |
| Doctor cancelling an entire day | Not implemented — see the dedicated section above. |
| Reschedule — original slot / atomicity | Same appointment row updated in place inside `transaction.atomic()`. |
| Reschedule — slot taken mid-request | Rejected via the same database constraint that prevents double-booking; I have a test proving the original appointment is left unchanged. |
| Availability for a past date | Returns `400`, not an empty list. An empty list would look identical to "fully booked" or "doctor doesn't work that day" — different problems needing different frontend messages. Kept consistent with `POST /appointments`, which also rejects past bookings outright. |
| Email vs. phone as the patient identifier | Email — cleaner path to add verification/password-reset later using Django's own tooling. |

## Known limitations — what I chose not to build, and why

- **No email verification or password reset.** A patient could
  register with an email they don't own. I'd close this in production
  with a confirmation-link flow via Django's
  `PasswordResetTokenGenerator` and a real email backend (SES/SendGrid).
  I didn't build it here because it pulls in external infrastructure
  disproportionate to what this assessment tests, and it's exactly the
  kind of dependency that fails quietly on a free-tier deployment.
- **No doctor / working-hours management API** — Django Admin only,
  since it's not part of the patient-facing surface the brief asks for.
- **No handling of a doctor cancelling an entire day** — designed
  above, intentionally not implemented.

## Growth considerations

The brief mentions the clinic is "starting small but want to grow," so
a few notes on what I'd revisit first:

- **Dynamic slot computation** is fine at 5 doctors. If this grew to
  many doctors with heavy traffic, I'd move to a materialized slot
  table or a cache layer in front of availability queries, since
  recomputing the full grid on every request gets more expensive as
  booking volume grows.
- **PostgreSQL in production, SQLite locally.** SQLite's coarse-grained
  locking doesn't handle concurrent writes well, and concurrent writes
  are exactly the scenario this whole design exists to protect against
  — so I made sure the deployed version runs on real Postgres.

---

## Authentication

Token-based, via `rest_framework.authtoken`.

1. `POST /api/patients/register/` — creates an account. Returns patient
   details, no token yet.
2. `POST /api/patients/login/` — exchanges email + password for a token.
3. Every appointment-mutating endpoint requires:
   ```
   Authorization: Token <token>
   ```
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

Full interactive documentation, generated from the actual serializers
(not hand-written, so it can't drift out of sync with the code):
**https://clinic-booking-api-cnnv.onrender.com/api/docs/**

**Validation enforced on every booking and reschedule** (each returns
`400` with a specific message on failure):
- Slot must fall within the doctor's working hours
- Slot must not be in the past
- Slot must be at least 1 hour from now
- Slot must not already be booked — also enforced at the database
  level, which returns `409` if two requests genuinely race for the
  same slot

See **"How to Test This"** above for a full worked example against the
live deployment, using real curl commands and real pre-seeded doctors.

---

## Running Locally

```bash
git clone https://github.com/Ndugere/clinic-booking-api.git
cd clinic-booking-api

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file at the project root (never committed — see
`.env.example` for the template):

```
SECRET_KEY=any-random-string-for-local-dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser   # for /admin
python manage.py runserver
```

### Seeding demo data

```bash
python manage.py seed_demo_data
```

Creates 5 doctors with realistic, varied working hours (different
specialties, different days/hours per doctor) — safe to run multiple
times, it checks for existing records by name and won't create
duplicates. This is the same command that runs automatically as part
of the production build on Render (see Deployment below), so the demo
dataset is reproducible identically in both places.

Visit `http://127.0.0.1:8000/admin` to inspect or add doctors and
`WorkingHours` manually if you'd rather, or
`http://127.0.0.1:8000/api/docs/` to explore and test the API directly
in the browser.

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

## Deployment

Deployed on **Render** — one PostgreSQL instance plus one Web Service,
connected directly to this GitHub repository.

**Build command:**
```
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py ensure_superuser && python manage.py seed_demo_data
```

**Start command:**
```
gunicorn config.wsgi:application
```

`ensure_superuser` and `seed_demo_data` are small custom management
commands
(`accounts/management/commands/ensure_superuser.py` and
`clinic/management/commands/seed_demo_data.py`) that create an admin
login and 5 demo doctors from environment variables / fixed data on
first deploy, and safely do nothing on every deploy after that. I
added these because Render's free tier doesn't provide shell access,
so there was no other way to get an initial admin login and
demonstrable data onto the production database without them.

Static files (Django Admin CSS/JS, the Swagger UI assets) are served
directly by the app in production via **WhiteNoise**, rather than
needing a separate static file host — the simplest option at this
scale.

**Known constraint:** Render's free-tier PostgreSQL instances expire
after 90 days and are deleted automatically. This is a platform limit,
not something in my control — for the purposes of this submission it
isn't a concern, but it's the first thing I'd change (upgrade to a
persistent paid tier, or add a backup/restore step) if this were
running long-term.

---

## CI/CD

Pipeline runs via **GitHub Actions**, defined in
`.github/workflows/ci-cd.yml`.

- **On every pull request to `main`:** the full test suite (28 tests
  across all three apps) runs automatically. A red check blocks
  merging with confidence that something's broken.
- **On every push to `main`** (i.e. after a PR merges): the same test
  suite runs again against the merged code, producing a GitHub Check
  result on that commit.
- **Deployment is gated on that check passing.** Render's own
  "Auto-Deploy: After CI Checks Pass" setting watches GitHub's Checks
  API and only triggers a deploy once the test job reports success —
  I chose this over Render's default "deploy on every commit" because
  it means a broken commit can never reach production, even if it
  somehow got merged. This ties deployment directly to test results
  rather than just to a successful `git push`.
- **Branch that triggers deployment:** `main`.

---

## Section 4: AI Reflection

See [`AI_REFLECTION.md`](./AI_REFLECTION.md).