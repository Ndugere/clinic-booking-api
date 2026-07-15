# Section 4: AI Reflection

## 1. What did I use AI for across the four sections?

- **System design (Section 1):** I used AI as a brainstorming and
  stress-testing partner rather than a source of final answers. For
  every ambiguous point in the brief — how to model working hours,
  whether to store slots as their own table, how to handle
  authentication, who should be allowed to book on whose behalf — I'd
  describe the problem, get back two or three options with their
  trade-offs, and then make the actual call myself. Several of my
  decisions (see Q4) directly overrode or extended what the AI first
  proposed.
- **API implementation (Section 2):** Once a design decision was
  locked in, I used AI to generate the Django/DRF code faster than I'd
  have written it by hand — serializers, views, validators — and then
  to verify it, including running the actual test suite and proving
  edge cases (like the double-booking race condition) actually behaved
  as designed, rather than just trusting that the code looked correct.
- **Testing:** I used AI to help build out test coverage for each app
  (accounts, clinic, appointments), including edge cases I prompted it
  with directly — ownership checks, cancelled-appointment handling,
  and the reschedule-into-a-taken-slot race condition.
- **Deployment & CI/CD (Section 3):** I used it to help write the
  GitHub Actions workflow. We discussed two viable approaches — a
  custom deploy job triggered via a Render deploy hook, versus relying
  on Render's own native "deploy only after CI checks pass" setting —
  and I chose the second once I found it in Render's actual dashboard,
  since it achieved the same guarantee (no broken code reaches
  production) with less custom pipeline logic to maintain.
- **Documentation:** I asked AI to help me add interactive API
  documentation (Swagger/Redoc via `drf-spectacular`) so the API would
  be genuinely usable by someone who isn't me, not just described in a
  README.

## 2. One example where an AI suggestion improved my work

**What I prompted it with:** When deciding on the CI/CD deployment
trigger, I asked it to lay out my options for tying deployment to test
results, along with the consequences of each, rather than just giving
me one answer.

**The improvement:** It proposed a custom two-job GitHub Actions
pipeline (a `test` job, then a `deploy` job gated with `needs: test`
that calls a Render deploy hook via a GitHub secret). That was a
reasonable, working design. But because I'd asked for the trade-offs
rather than just a solution, I went looking at what Render itself
offered before committing — and found Render has a native
`autoDeployTrigger` setting, "After CI Checks Pass," that achieves the
exact same guarantee natively, without me having to maintain a custom
deploy job, a secret URL, or the two-job dependency logic myself. I
ended up using Render's native option instead, but the AI's
options-with-consequences framing is what pushed me to actually check
the platform's own capabilities before building something custom on
top of it — which is a habit I want to keep.

## 3. One example where AI output was wrong or incomplete, and how I caught it

Early in the system design phase, when I asked AI to help design
authentication for the booking endpoints, its first proposed design
was to have **no authentication at all** — appointments would be
created, cancelled, and rescheduled using only IDs passed in the
request body, with no verification of who was making the request.

I caught this as a real security gap myself: nothing in that design
stopped one patient from guessing or enumerating another patient's
appointment ID and cancelling or rescheduling it, since there was no
check tying a request to the person who actually owns that
appointment. I pushed back on this directly, and we went through
several iterations — from no auth, to a receptionist-mediated booking
model, to finally a token-based auth system where the patient's
identity is always derived from their auth token rather than from any
ID they could supply in a request. I then confirmed this was actually
enforced by testing it directly: attempting to cancel and reschedule
one patient's appointment using a different patient's token, and
verifying the API correctly returns a `403 Forbidden` in both cases —
which is now a permanent part of the automated test suite, not just a
manual check.

## 4. Two decisions I made without AI, and why I trusted my own judgment

- **Requiring password-based authentication, not just a bare token.**
  When the AI's initial design didn't include any authentication at
  all, I was the one who pushed for real security controls, since I
  knew this was meant to represent a real clinic system handling real
  patient data — a bare, non-recoverable token felt inadequate the
  moment I thought about what happens when a patient loses it. I
  trusted my own judgment here because it wasn't a technical
  correctness question, it was a product/security instinct about what
  a real system handling personal health information actually needs,
  which I felt was mine to own rather than defer on.

- **Keeping doctor management admin-only, via Django Admin, rather
  than letting doctors self-register or self-manage their schedules.**
  This is the kind of decision that comes down to understanding the
  real-world system being modeled, not just the technical options. I
  reasoned that this brief describes a real hospital/clinic, where
  management assigns doctors and tracks their availability
  centrally — not a freelance marketplace where a doctor sets their
  own hours independently. Once I framed it that way, keeping doctor
  and working-hours management behind Django Admin (rather than
  building a public doctor-facing API that wasn't asked for) was an
  easy, confident call, because it followed directly from what kind of
  system this actually is.