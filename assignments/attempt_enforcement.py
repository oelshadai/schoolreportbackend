"""
Phase 4: Attempt Limit Enforcement Logic
Atomic operations with database-level constraints
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models_phase4_enforcement import StudentAssignment, AcademicViolation


class AttemptLimitEnforcer:
    """Backend attempt limit enforcement with atomic operations"""
    
    @staticmethod
    @transaction.atomic
    def validate_attempt_eligibility(student_assignment):
        """Validate if student can start new attempt"""
        
        # Lock the record for atomic update
        locked_assignment = StudentAssignment.objects.select_for_update().get(
            pk=student_assignment.pk
        )
        
        # Check attempt count against limit
        if locked_assignment.attempts_count >= locked_assignment.assignment.max_attempts:
            raise ValidationError(
                f'Maximum attempts exceeded: {locked_assignment.attempts_count}/'
                f'{locked_assignment.assignment.max_attempts}'
            )
        
        # Check current status
        if locked_assignment.status in ['SUBMITTED', 'GRADED', 'LOCKED', 'EXPIRED', 'VIOLATED']:
            raise ValidationError(f'Cannot start attempt: assignment is {locked_assignment.status}')
        
        # Check if already in progress
        if locked_assignment.status == 'IN_PROGRESS':
            if locked_assignment.current_attempt_started_at:
                # Check if previous attempt expired
                if locked_assignment.assignment.is_timed:
                    elapsed = timezone.now() - locked_assignment.current_attempt_started_at
                    time_limit_seconds = locked_assignment.assignment.time_limit_minutes * 60
                    
                    if elapsed.total_seconds() > time_limit_seconds:
                        # Auto-expire previous attempt
                        locked_assignment.status = 'EXPIRED'
                        locked_assignment.is_locked = False
                        locked_assignment.save()
                    else:
                        raise ValidationError('Previous attempt still in progress')
                else:
                    raise ValidationError('Previous attempt still in progress')
        
        # Check assignment availability window
        now = timezone.now()
        if now < locked_assignment.assignment.start_date:
            raise ValidationError('Assignment not yet available')
        
        if now > locked_assignment.assignment.due_date:
            locked_assignment.status = 'EXPIRED'
            locked_assignment.save()
            raise ValidationError('Assignment deadline has passed')
        
        return locked_assignment
    
    @staticmethod
    @transaction.atomic
    def start_new_attempt(student_assignment):
        """Start new attempt with atomic increment"""
        
        # Validate eligibility first
        validated_assignment = AttemptLimitEnforcer.validate_attempt_eligibility(student_assignment)
        
        # Increment attempt count atomically
        validated_assignment.attempts_count += 1
        validated_assignment.current_attempt_started_at = timezone.now()
        validated_assignment.last_activity_at = timezone.now()
        validated_assignment.status = 'IN_PROGRESS'
        
        # Apply exam lockdown if required
        if validated_assignment.assignment.assignment_type == 'EXAM':
            validated_assignment.is_locked = True
            validated_assignment.assignment.requires_lockdown = True
        
        validated_assignment.save()
        
        return validated_assignment
    
    @staticmethod
    def get_attempt_status(student_assignment):
        """Get current attempt status with enforcement"""
        
        # Auto-expire if needed
        if student_assignment.status == 'IN_PROGRESS' and student_assignment.assignment.is_timed:
            if student_assignment.current_attempt_started_at:
                elapsed = timezone.now() - student_assignment.current_attempt_started_at
                time_limit_seconds = student_assignment.assignment.time_limit_minutes * 60
                
                if elapsed.total_seconds() > time_limit_seconds:
                    student_assignment.status = 'EXPIRED'
                    student_assignment.is_locked = False
                    student_assignment.save()
        
        return {
            'attempts_used': student_assignment.attempts_count,
            'max_attempts': student_assignment.assignment.max_attempts,
            'attempts_remaining': student_assignment.assignment.max_attempts - student_assignment.attempts_count,
            'can_attempt': student_assignment.attempts_count < student_assignment.assignment.max_attempts,
            'status': student_assignment.status,
            'is_locked': student_assignment.is_locked
        }
    
    @staticmethod
    @transaction.atomic
    def handle_violation(student_assignment, violation_type, description):
        """Handle academic violation with attempt impact"""
        
        # Record violation
        violation = AcademicViolation.objects.create(
            student_assignment=student_assignment,
            violation_type=violation_type,
            description=description
        )
        
        # Increment violation count
        student_assignment.lockdown_violations += 1
        
        # Enforce violation consequences
        if violation_type == 'TIME_EXCEEDED':
            # Auto-expire for time violations
            student_assignment.status = 'EXPIRED'
            student_assignment.is_locked = False
        
        elif violation_type in ['LOCKDOWN_BREACH', 'MULTIPLE_TABS']:
            # Severe violations - lock assignment
            if student_assignment.lockdown_violations >= 2:
                student_assignment.status = 'VIOLATED'
                student_assignment.is_locked = True
        
        elif student_assignment.lockdown_violations >= 3:
            # Too many violations - flag for review
            student_assignment.status = 'VIOLATED'
            student_assignment.is_locked = True
        
        student_assignment.save()
        
        return violation


class ExamAttemptEnforcer(AttemptLimitEnforcer):
    """Specialized enforcer for exam attempts"""
    
    @staticmethod
    @transaction.atomic
    def validate_exam_attempt(student_assignment):
        """Strict validation for exam attempts"""
        
        if student_assignment.assignment.assignment_type != 'EXAM':
            raise ValidationError('Not an exam assignment')
        
        # Exams allow only 1 attempt - database constraint enforces this
        if student_assignment.attempts_count >= 1:
            raise ValidationError('Exams allow only one attempt')
        
        # Exams must be timed
        if not student_assignment.assignment.is_timed or not student_assignment.assignment.time_limit_minutes:
            raise ValidationError('Exam must have time limit')
        
        # Call parent validation
        return AttemptLimitEnforcer.validate_attempt_eligibility(student_assignment)
    
    @staticmethod
    @transaction.atomic
    def start_exam_attempt(student_assignment):
        """Start exam with full lockdown"""
        
        # Validate exam eligibility
        validated_assignment = ExamAttemptEnforcer.validate_exam_attempt(student_assignment)
        
        # Start attempt with lockdown
        validated_assignment.attempts_count = 1  # Exams get exactly 1 attempt
        validated_assignment.current_attempt_started_at = timezone.now()
        validated_assignment.last_activity_at = timezone.now()
        validated_assignment.status = 'IN_PROGRESS'
        validated_assignment.is_locked = True  # Full lockdown for exams
        
        validated_assignment.save()
        
        return validated_assignment