from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed production database with essential school and user accounts'

    def handle(self, *args, **options):
        self.stdout.write('Seeding production data...')
        try:
            with transaction.atomic():
                school = self._ensure_school()
                self._ensure_users(school)
            self.stdout.write(self.style.SUCCESS('Production seed complete.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Seed failed: {e}'))
            raise

    def _ensure_school(self):
        from schools.models import School
        school, created = School.objects.get_or_create(
            name='Ansar Educational complex',
            defaults={
                'address': 'Kumasi',
                'location': 'Nwamae-Bosore',
                'phone_number': '0204064927',
                'email': 'oelshadai565@gmail.com',
                'motto': 'Learning To Build',
                'current_academic_year': '2025-2026',
                'score_entry_mode': 'CLASS_TEACHER',
                'report_template': 'GHANA_EDUCATION_SERVICE',
                'show_class_average': True,
                'show_position_in_class': True,
                'show_attendance': True,
                'show_behavior_comments': True,
                'is_active': True,
                'subscription_plan': 'FREE',
            }
        )
        if created:
            self.stdout.write(f'  Created school: {school.name}')
        else:
            self.stdout.write(f'  School exists: {school.name}')
        return school

    def _ensure_users(self, school):
        accounts = [
            # (email, password, first, last, role, is_staff, is_superuser)
            ('oelshadai565@gmail.com', 'Admin@1234', 'osei', 'elshadai', 'SCHOOL_ADMIN', False, False),
            ('oseielshadai18@gmail.com', 'Admin@1234', 'osei', 'elshadai', 'TEACHER', False, False),
            ('nanaamaadomah18@gmail.com', 'Nanama22.', 'ADOMAH', 'JACKLINE', 'TEACHER', False, False),
            ('admin@example.com', 'Admin@1234', 'Admin', 'User', 'SUPER_ADMIN', True, True),
        ]

        for email, password, first, last, role, is_staff, is_superuser in accounts:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'is_active': True,
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                    'school': school,
                }
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created user: {email} ({role})')
            else:
                # Always reset password and ensure active in case it was broken
                user.set_password(password)
                user.is_active = True
                user.role = role
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                if not user.school:
                    user.school = school
                user.save()
                self.stdout.write(f'  Updated user: {email} ({role})')
