"""
Academic Cleanup Management Command
Handles expired assignments and time limits
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from assignments.models import StudentAssignment


class Command(BaseCommand):
    help = 'Handle expired assignments and enforce time limits'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find expired assignments
        expired_assignments = StudentAssignment.objects.filter(
            status='IN_PROGRESS',
            assignment__is_timed=True,
            current_attempt_started_at__isnull=False
        )
        
        expired_count = 0
        
        for student_assignment in expired_assignments:
            if student_assignment.check_time_limit():
                if dry_run:
                    self.stdout.write(
                        f'Would expire: {student_assignment.assignment.title} '
                        f'for {student_assignment.student.get_full_name()}'
                    )
                else:
                    student_assignment.auto_submit_if_expired()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Expired: {student_assignment.assignment.title} '
                            f'for {student_assignment.student.get_full_name()}'
                        )
                    )
                expired_count += 1
        
        if expired_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired assignments found')
            )
        else:
            action = 'Would expire' if dry_run else 'Expired'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} {expired_count} assignment(s)'
                )
            )