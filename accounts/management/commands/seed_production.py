import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Bootstrap the SaaS owner superadmin account from environment variables'

    def handle(self, *args, **options):
        self.stdout.write('Ensuring SaaS owner superadmin access...')
        try:
            with transaction.atomic():
                self._ensure_superadmin()
            self.stdout.write(self.style.SUCCESS('Superadmin bootstrap complete.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Seed failed: {e}'))
            raise

    def _ensure_superadmin(self):
        email = os.getenv('SUPERADMIN_EMAIL', '').strip().lower()
        password = os.getenv('SUPERADMIN_PASSWORD', '').strip()

        if not email or not password:
            self.stdout.write(self.style.WARNING('  Superadmin bootstrap skipped: set SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD.'))
            return

        first_name = os.getenv('SUPERADMIN_FIRST_NAME', 'SaaS').strip() or 'SaaS'
        last_name = os.getenv('SUPERADMIN_LAST_NAME', 'Owner').strip() or 'Owner'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'SUPER_ADMIN',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        user.first_name = first_name
        user.last_name = last_name
        user.role = 'SUPER_ADMIN'
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.school = None
        user.set_password(password)
        user.save()

        self.stdout.write(
            f"  {'Created' if created else 'Updated'} superadmin: {email}"
        )
