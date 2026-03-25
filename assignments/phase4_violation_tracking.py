"""
Phase 4: Violation Tracking Service
Minimal violation tracking and reporting
"""
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class ViolationTrackingService:
    """Minimal violation tracking service"""
    
    @staticmethod
    def record_violation(student_assignment, violation_type, description=""):
        """Record academic violation"""
        from .models_phase4_final import AcademicViolation
        
        try:
            with transaction.atomic():
                violation = AcademicViolation.objects.create(
                    student_assignment=student_assignment,
                    violation_type=violation_type,
                    description=description
                )
                
                # Update violation count
                student_assignment.lockdown_violations += 1
                
                # Auto-fail for serious violations
                if violation_type in ['LOCKDOWN_BREACH', 'MULTIPLE_TABS']:
                    if student_assignment.assignment.assignment_type == 'EXAM':
                        student_assignment.status = 'VIOLATED'
                        student_assignment.is_locked = False
                
                student_assignment.save()
                
                logger.warning(f"Violation recorded: {violation_type} for student {student_assignment.student.id}")
                return violation
                
        except Exception as e:
            logger.error(f"Failed to record violation: {str(e)}")
            return None
    
    @staticmethod
    def get_violation_summary(student_id, days=30):
        """Get violation summary for student"""
        from .models_phase4_final import AcademicViolation
        
        since = timezone.now() - timezone.timedelta(days=days)
        violations = AcademicViolation.objects.filter(
            student_assignment__student_id=student_id,
            created_at__gte=since
        ).values('violation_type').distinct()
        
        return {
            'total_violations': violations.count(),
            'violation_types': list(violations),
            'period_days': days
        }
    
    @staticmethod
    def check_violation_threshold(student_assignment):
        """Check if violation threshold exceeded"""
        threshold = 3  # Max violations before auto-fail
        
        if student_assignment.lockdown_violations >= threshold:
            if student_assignment.assignment.assignment_type in ['EXAM', 'QUIZ']:
                student_assignment.status = 'VIOLATED'
                student_assignment.is_locked = False
                student_assignment.save()
                
                logger.warning(f"Student {student_assignment.student.id} auto-failed due to violations")
                return True
        
        return False
    
    @staticmethod
    def get_lockdown_status(student_assignment):
        """Get lockdown status for assignment"""
        if not student_assignment.assignment.requires_lockdown:
            return {'required': False, 'active': False}
        
        return {
            'required': True,
            'active': student_assignment.status == 'IN_PROGRESS',
            'violations': student_assignment.lockdown_violations,
            'max_violations': 3
        }