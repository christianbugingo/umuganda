import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a superuser from environment variables if the account is absent.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        if not any((username, email, password)):
            self.stdout.write('No bootstrap admin credentials configured; skipping.')
            return
        if not all((username, email, password)):
            raise CommandError(
                'Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, '
                'and DJANGO_SUPERUSER_PASSWORD together.'
            )

        user_model = get_user_model()
        existing_user = user_model.objects.filter(username=username).first()
        if existing_user:
            if not existing_user.is_superuser:
                raise CommandError(
                    'The configured bootstrap username belongs to a non-superuser.'
                )
            self.stdout.write('Bootstrap superuser already exists; leaving it unchanged.')
            return

        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write('Bootstrap superuser created.')
