"""
Phase 4: Time Enforcement Service
Minimal time-based enforcement for assignments
"""
from django.utils import timezone
from django.db import transaction
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


class TimeEnforcementService:
    """Minimal time enforcement service"""
    
    @staticmethod
    def check_time_violations():
        """Check and enforce time-based violations"""
        from .models_phase4_final import StudentAssignment
        
        now = timezone.now()
        expired_assignments = StudentAssignment.objects.filter(
            status='IN_PROGRESS',
            current_attempt_started_at__isnull=False
        ).select_related('assignment')
        
        violations = 0
        for student_assignment in expired_assignments:
            if student_assignment.assignment.time_limit_minutes:
                time_limit = timezone.timedelta(minutes=student_assignment.assignment.time_limit_minutes)
                if now - student_assignment.current_attempt_started_at > time_limit:
                    student_assignment.auto_expire_if_needed()
                    violations += 1
        
        logger.info(f"Time enforcement check: {violations} assignments auto-expired")
        return violations
    
    @staticmethod
    def get_time_remaining(student_assignment):
        """Get remaining time for assignment"""
        if not student_assignment.current_attempt_started_at:
            return None
        
        if not student_assignment.assignment.time_limit_minutes:
            return None
        
        elapsed = timezone.now() - student_assignment.current_attempt_started_at
        limit = timezone.timedelta(minutes=student_assignment.assignment.time_limit_minutes)
        remaining = limit - elapsed
        
        return max(0, remaining.total_seconds())


@shared_task
def auto_expire_assignments():
    """Celery task to auto-expire assignments"""
    try:
        violations = TimeEnforcementService.check_time_violations()
        logger.info(f"Auto-expire task completed: {violations} assignments processed")
        return violations
    except Exception as e:
        logger.error(f"Auto-expire task failed: {str(e)}")
        return 0