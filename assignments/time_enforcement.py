from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Assignment, StudentSubmission

class TimeEnforcement:
    @staticmethod
    @transaction.atomic
    def check_time_limit(assignment_id, student_id):
        """Check if student can still submit based on time limits"""
        assignment = Assignment.objects.select_for_update().get(id=assignment_id)
        
        # Check assignment deadline
        if assignment.due_date and timezone.now() > assignment.due_date:
            return False, "Assignment deadline has passed"
        
        # Check individual time limit
        if assignment.time_limit_minutes:
            submission = StudentSubmission.objects.filter(
                assignment_id=assignment_id, 
                student_id=student_id,
                status='IN_PROGRESS'
            ).first()
            
            if submission:
                elapsed = timezone.now() - submission.started_at
                if elapsed.total_seconds() > assignment.time_limit_minutes * 60:
                    submission.status = 'EXPIRED'
                    submission.save()
                    return False, "Time limit exceeded"
        
        return True, "Time check passed"
    
    @staticmethod
    def expire_overdue_submissions():
        """Automatically expire submissions that exceed time limits"""
        overdue = StudentSubmission.objects.filter(
            status='IN_PROGRESS',
            assignment__time_limit_minutes__isnull=False
        ).select_related('assignment')
        
        expired_count = 0
        for submission in overdue:
            elapsed = timezone.now() - submission.started_at
            if elapsed.total_seconds() > submission.assignment.time_limit_minutes * 60:
                submission.status = 'EXPIRED'
                submission.save()
                expired_count += 1
        
        return expired_count