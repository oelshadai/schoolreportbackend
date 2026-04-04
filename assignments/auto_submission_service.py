"""
Auto-submission service for handling overdue assignments
Automatically submits assignments when due date passes
"""
from django.utils import timezone
from django.db import transaction
from django.core.management.base import BaseCommand
from .models import Assignment, StudentAssignment, QuizAttempt
import logging

logger = logging.getLogger(__name__)

class AutoSubmissionService:
    """Service to handle automatic submission of overdue assignments"""
    
    @staticmethod
    def process_overdue_assignments():
        """Process all overdue assignments and auto-submit them"""
        now = timezone.now()
        
        # Find all published assignments that are past due date
        overdue_assignments = Assignment.objects.filter(
            status='PUBLISHED',
            due_date__lt=now
        )
        
        auto_submitted_count = 0
        
        for assignment in overdue_assignments:
            # Find students who haven't submitted yet
            unsubmitted_students = StudentAssignment.objects.filter(
                assignment=assignment,
                status__in=['NOT_STARTED', 'IN_PROGRESS']
            )
            
            for student_assignment in unsubmitted_students:
                try:
                    with transaction.atomic():
                        # Auto-submit the assignment
                        student_assignment.status = 'SUBMITTED'
                        student_assignment.submitted_at = now
                        student_assignment.submission_text = "Auto-submitted due to deadline expiry"
                        
                        # For quiz/exam assignments, create empty attempt
                        if assignment.assignment_type in ['QUIZ', 'EXAM']:
                            quiz_attempt, created = QuizAttempt.objects.get_or_create(
                                assignment=assignment,
                                student=student_assignment.student,
                                defaults={
                                    'status': 'SUBMITTED',
                                    'submitted_at': now,
                                    'score': 0  # Zero score for auto-submitted
                                }
                            )
                            
                            # Mark student assignment as graded with zero score
                            student_assignment.status = 'GRADED'
                            student_assignment.score = 0
                            student_assignment.graded_at = now
                            student_assignment.teacher_feedback = "Assignment auto-submitted after deadline. No score awarded."
                        
                        student_assignment.save()
                        auto_submitted_count += 1
                        
                        logger.info(f"Auto-submitted assignment {assignment.title} for student {student_assignment.student.get_full_name()}")
                        
                except Exception as e:
                    logger.error(f"Failed to auto-submit assignment {assignment.id} for student {student_assignment.student.id}: {e}")
                    continue
        
        return auto_submitted_count
    
    @staticmethod
    def process_expired_timed_assignments():
        """Process timed assignments that have exceeded their time limit"""
        now = timezone.now()
        expired_count = 0
        
        # Find in-progress timed assignments
        in_progress_assignments = StudentAssignment.objects.filter(
            status='IN_PROGRESS',
            assignment__is_timed=True,
            current_attempt_started_at__isnull=False
        )
        
        for student_assignment in in_progress_assignments:
            if student_assignment.check_time_limit():
                try:
                    with transaction.atomic():
                        student_assignment.auto_submit_if_expired()
                        expired_count += 1
                        logger.info(f"Auto-submitted expired timed assignment {student_assignment.assignment.title} for {student_assignment.student.get_full_name()}")
                except Exception as e:
                    logger.error(f"Failed to auto-submit expired assignment {student_assignment.id}: {e}")
                    continue
        
        return expired_count


class Command(BaseCommand):
    help = 'Auto-submit overdue and expired assignments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made')
        
        # Process overdue assignments
        if not dry_run:
            overdue_count = AutoSubmissionService.process_overdue_assignments()
            expired_count = AutoSubmissionService.process_expired_timed_assignments()
        else:
            # For dry run, just count what would be processed
            now = timezone.now()
            overdue_assignments = Assignment.objects.filter(
                status='PUBLISHED',
                due_date__lt=now
            )
            
            overdue_count = 0
            for assignment in overdue_assignments:
                count = StudentAssignment.objects.filter(
                    assignment=assignment,
                    status__in=['NOT_STARTED', 'IN_PROGRESS']
                ).count()
                overdue_count += count
            
            expired_count = StudentAssignment.objects.filter(
                status='IN_PROGRESS',
                assignment__is_timed=True,
                current_attempt_started_at__isnull=False
            ).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{"Would process" if dry_run else "Processed"} {overdue_count} overdue assignments and {expired_count} expired timed assignments'
            )
        )