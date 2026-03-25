from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid

class AcademicEnforcementRule(models.Model):
    """Core enforcement rules with database-level constraints"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    rule_type = models.CharField(max_length=50, choices=[
        ('ATTEMPT_LIMIT', 'Attempt Limit'),
        ('TIME_LIMIT', 'Time Limit'),
        ('SUBMISSION_WINDOW', 'Submission Window'),
        ('ACADEMIC_INTEGRITY', 'Academic Integrity')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'academic_enforcement_rules'
        constraints = [
            models.UniqueConstraint(
                fields=['rule_type'], 
                condition=models.Q(is_active=True),
                name='unique_active_rule_per_type'
            )
        ]

class AssignmentEnforcement(models.Model):
    """Assignment-specific enforcement with atomic operations"""
    assignment = models.OneToOneField('Assignment', on_delete=models.CASCADE, related_name='enforcement')
    max_attempts = models.PositiveIntegerField(default=3)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    submission_deadline = models.DateTimeField()
    late_submission_penalty = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    auto_submit_on_timeout = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'assignment_enforcement'
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_attempts__gte=1, max_attempts__lte=10),
                name='valid_attempt_range'
            ),
            models.CheckConstraint(
                check=models.Q(time_limit_minutes__gte=5) | models.Q(time_limit_minutes__isnull=True),
                name='valid_time_limit'
            )
        ]

class StudentSubmissionAttempt(models.Model):
    """Track submission attempts with enforcement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE)
    attempt_number = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_expired_at = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    violation_reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'student_submission_attempts'
        unique_together = ['student', 'assignment', 'attempt_number']
        constraints = [
            models.CheckConstraint(
                check=models.Q(attempt_number__gte=1),
                name='positive_attempt_number'
            )
        ]
    
    @transaction.atomic
    def validate_attempt(self):
        """Atomic validation of submission attempt"""
        enforcement = self.assignment.enforcement
        
        # Check attempt limit
        if self.attempt_number > enforcement.max_attempts:
            self.is_valid = False
            self.violation_reason = f"Exceeded maximum attempts ({enforcement.max_attempts})"
            self.save()
            raise ValidationError("Maximum attempts exceeded")
        
        # Check time limit
        if enforcement.time_limit_minutes:
            time_limit = timedelta(minutes=enforcement.time_limit_minutes)
            if timezone.now() > self.started_at + time_limit:
                self.is_valid = False
                self.time_expired_at = timezone.now()
                self.violation_reason = "Time limit exceeded"
                self.save()
                raise ValidationError("Time limit exceeded")
        
        return True

class SubmissionEnforcementLog(models.Model):
    """Audit log for enforcement actions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    attempt = models.ForeignKey(StudentSubmissionAttempt, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=[
        ('ATTEMPT_BLOCKED', 'Attempt Blocked'),
        ('TIME_EXPIRED', 'Time Expired'),
        ('AUTO_SUBMITTED', 'Auto Submitted'),
        ('VIOLATION_DETECTED', 'Violation Detected')
    ])
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'submission_enforcement_log'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['action'])
        ]

class AcademicViolation(models.Model):
    """Track academic violations with severity levels"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE)
    violation_type = models.CharField(max_length=50, choices=[
        ('ATTEMPT_EXCEEDED', 'Attempt Limit Exceeded'),
        ('TIME_EXCEEDED', 'Time Limit Exceeded'),
        ('LATE_SUBMISSION', 'Late Submission'),
        ('INTEGRITY_BREACH', 'Academic Integrity Breach')
    ])
    severity = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical')
    ])
    penalty_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'academic_violations'
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['violation_type', 'severity'])
        ]

# Enforcement Manager for atomic operations
class EnforcementManager:
    """Centralized enforcement operations with atomic transactions"""
    
    @staticmethod
    @transaction.atomic
    def create_attempt(student, assignment):
        """Create new submission attempt with validation"""
        enforcement = assignment.enforcement
        existing_attempts = StudentSubmissionAttempt.objects.filter(
            student=student, assignment=assignment
        ).count()
        
        if existing_attempts >= enforcement.max_attempts:
            AcademicViolation.objects.create(
                student=student,
                assignment=assignment,
                violation_type='ATTEMPT_EXCEEDED',
                severity='HIGH'
            )
            raise ValidationError("Maximum attempts exceeded")
        
        attempt = StudentSubmissionAttempt.objects.create(
            student=student,
            assignment=assignment,
            attempt_number=existing_attempts + 1
        )
        
        return attempt
    
    @staticmethod
    @transaction.atomic
    def submit_attempt(attempt, submission_data):
        """Submit attempt with enforcement validation"""
        try:
            attempt.validate_attempt()
            attempt.submitted_at = timezone.now()
            attempt.save()
            
            SubmissionEnforcementLog.objects.create(
                attempt=attempt,
                action='ATTEMPT_SUBMITTED',
                details={'submission_time': attempt.submitted_at.isoformat()}
            )
            
            return True
        except ValidationError as e:
            SubmissionEnforcementLog.objects.create(
                attempt=attempt,
                action='VIOLATION_DETECTED',
                details={'error': str(e)}
            )
            raise
    
    @staticmethod
    @transaction.atomic
    def auto_submit_expired(attempt):
        """Auto-submit when time expires"""
        attempt.time_expired_at = timezone.now()
        attempt.submitted_at = timezone.now()
        attempt.save()
        
        SubmissionEnforcementLog.objects.create(
            attempt=attempt,
            action='AUTO_SUBMITTED',
            details={'reason': 'time_expired'}
        )