import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Creates a Django superuser from environment variables, if one with
    that username does not already exist.

    Safe to run on every deploy (idempotent) -- intended to be chained
    into the Render build command so a fresh production database always
    has an admin login available, without needing shell access (not
    available on Render's free tier).

    Required env vars: DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL,
    DJANGO_SUPERUSER_PASSWORD. If any are missing, the command exits
    quietly without creating anything -- so it's also safe to leave in
    the build command for local/CI environments that don't set these.
    """

    help = "Creates a superuser from DJANGO_SUPERUSER_* env vars if one doesn't already exist."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            self.stdout.write(
                "DJANGO_SUPERUSER_* env vars not fully set -- skipping superuser creation."
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists -- skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))