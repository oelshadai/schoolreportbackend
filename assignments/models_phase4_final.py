"""
Phase 4: Final Backend Academic Enforcement Models
Complete backend authority with atomic transactions and database constraints
"""
from django.db import models, transaction
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from students.models import Student
from schools.models import ClassSubject, Class, Term


class Assignment(models.Model):
    """Assignment with complete backend enforcement"""
    
    ASSIGNMENT_TYPES = [
        ('HOMEWORK', 'Homework'),
        ('PROJECT', 'Project Work'),
        ('EXERCISE', 'Class Exercise'),
        ('QUIZ', 'Quiz'),
        ('EXAM', 'Exam'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('CLOSED', 'Closed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES)
    
    # Required academic targeting
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='assignments')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assignments')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_assignments')
    
    # Time constraints
    start_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Attempt constraints
    max_attempts = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    max_score = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    
    # Academic flags
    is_timed = models.BooleanField(default=False)
    requires_lockdown = models.BooleanField(default=False)
    auto_submit_on_timeout = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    published_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments_phase4'
        constraints = [
            models.CheckConstraint(
                check=models.Q(due_date__gt=models.F('start_date')),
                name='due_after_start'
            ),
            models.CheckConstraint(
                check=models.Q(max_score__gt=0),
                name='positive_max_score'
            ),
            models.CheckConstraint(
                check=models.Q(max_attempts__gt=0),
                name='positive_max_attempts'
            ),
            # Exam constraints
            models.CheckConstraint(
                check=~models.Q(assignment_type='EXAM') | models.Q(max_attempts=1),
                name='exam_single_attempt'
            ),
            models.CheckConstraint(
                check=~models.Q(assignment_type='EXAM') | (models.Q(is_timed=True) & ~models.Q(time_limit_minutes__isnull=True)),
                name='exam_must_be_timed'
            ),
        ]
    
    def clean(self):
        """Backend academic rule validation"""
        errors = {}
        
        # Teacher authorization
        if self.class_subject and self.created_by:
            if self.class_subject.teacher != self.created_by:
                errors['class_subject'] = 'You do not teach this subject'
        
        # Type-specific rules
        if self.assignment_type == 'EXAM':
            if self.max_attempts != 1:
                errors['max_attempts'] = 'Exams allow only 1 attempt'
            if not self.is_timed or not self.time_limit_minutes:
                errors['time_limit_minutes'] = 'Exams must be timed'
            self.requires_lockdown = True
            self.auto_submit_on_timeout = True
        
        if self.assignment_type == 'QUIZ':
            if not self.is_timed:
                self.is_timed = True
            if not self.time_limit_minutes:
                self.time_limit_minutes = 30
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == 'PUBLISHED' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class StudentAssignment(models.Model):
    """Student assignment with atomic enforcement"""
    
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
        ('LOCKED', 'Locked'),
        ('EXPIRED', 'Expired'),
        ('VIOLATED', 'Academic Violation'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='student_assignments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignments')
    
    # Attempt tracking
    attempts_count = models.PositiveIntegerField(default=0)
    current_attempt_started_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    
    # Submission data
    submission_text = models.TextField(blank=True)
    submission_file = models.FileField(upload_to='submissions/', null=True, blank=True)
    
    # Academic tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    is_locked = models.BooleanField(default=False)
    lockdown_violations = models.PositiveIntegerField(default=0)
    
    # Immutable timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # Grading
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_assignments_phase4'
        unique_together = ['assignment', 'student']
        constraints = [
            models.CheckConstraint(
                check=models.Q(attempts_count__gte=0),
                name='non_negative_attempts'
            ),
            models.CheckConstraint(
                check=models.Q(lockdown_violations__gte=0),
                name='non_negative_violations'
            ),
        ]
    
    @transaction.atomic
    def start_attempt(self):
        """Atomic attempt start with enforcement"""
        locked_instance = StudentAssignment.objects.select_for_update().get(pk=self.pk)
        
        # Validate attempt eligibility
        if locked_instance.attempts_count >= locked_instance.assignment.max_attempts:
            raise ValidationError(f'Maximum attempts ({locked_instance.assignment.max_attempts}) exceeded')
        
        if locked_instance.status in ['SUBMITTED', 'GRADED', 'LOCKED', 'EXPIRED', 'VIOLATED']:
            raise ValidationError(f'Cannot start attempt: status is {locked_instance.status}')
        
        # Check assignment availability
        now = timezone.now()
        if now < locked_instance.assignment.start_date:
            raise ValidationError('Assignment not yet available')
        
        if now > locked_instance.assignment.due_date:
            locked_instance.status = 'EXPIRED'
            locked_instance.save()
            raise ValidationError('Assignment deadline passed')
        
        # Start attempt
        locked_instance.attempts_count += 1
        locked_instance.current_attempt_started_at = now
        locked_instance.last_activity_at = now
        locked_instance.status = 'IN_PROGRESS'
        
        if locked_instance.assignment.requires_lockdown:
            locked_instance.is_locked = True
        
        locked_instance.save()
        return locked_instance
    
    @transaction.atomic
    def submit_assignment(self, submission_data=None):
        """Atomic submission with validation"""
        locked_instance = StudentAssignment.objects.select_for_update().get(pk=self.pk)
        
        if locked_instance.status != 'IN_PROGRESS':
            raise ValidationError(f'Cannot submit: status is {locked_instance.status}')
        
        # Time limit enforcement
        if locked_instance.assignment.is_timed and locked_instance.current_attempt_started_at:
            elapsed = timezone.now() - locked_instance.current_attempt_started_at
            if elapsed.total_seconds() > (locked_instance.assignment.time_limit_minutes * 60):
                if locked_instance.assignment.auto_submit_on_timeout:
                    locked_instance.status = 'EXPIRED'
                    locked_instance.save()
                    return locked_instance
                else:
                    raise ValidationError('Time limit exceeded')
        
        # Type-specific validation
        if locked_instance.assignment.assignment_type == 'PROJECT':
            if not submission_data or not submission_data.get('file'):
                raise ValidationError('Projects require file submission')
        
        # Submit
        now = timezone.now()
        locked_instance.status = 'SUBMITTED'
        locked_instance.submitted_at = now
        locked_instance.is_locked = False
        
        if submission_data:
            if submission_data.get('text'):
                locked_instance.submission_text = submission_data['text']
            if submission_data.get('file'):
                locked_instance.submission_file = submission_data['file']
        
        locked_instance.save()
        return locked_instance
    
    def check_time_remaining(self):
        """Get time remaining in seconds"""
        if not self.assignment.is_timed or not self.current_attempt_started_at:
            return None
        
        elapsed = timezone.now() - self.current_attempt_started_at
        remaining = (self.assignment.time_limit_minutes * 60) - elapsed.total_seconds()
        return max(0, int(remaining))
    
    def auto_expire_if_needed(self):
        """Auto-expire if time limit exceeded"""
        if (self.status == 'IN_PROGRESS' and 
            self.assignment.is_timed and 
            self.current_attempt_started_at):
            
            elapsed = timezone.now() - self.current_attempt_started_at
            if elapsed.total_seconds() > (self.assignment.time_limit_minutes * 60):
                self.status = 'EXPIRED'
                self.is_locked = False
                self.save()
                return True
        return False


class AcademicViolation(models.Model):
    """Track academic violations"""
    
    VIOLATION_TYPES = [
        ('TIME_EXCEEDED', 'Time Limit Exceeded'),
        ('MULTIPLE_TABS', 'Multiple Tabs Detected'),
        ('COPY_PASTE', 'Copy/Paste Detected'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('LOCKDOWN_BREACH', 'Lockdown Breach'),
    ]
    
    student_assignment = models.ForeignKey(StudentAssignment, on_delete=models.CASCADE, related_name='violations')
    violation_type = models.CharField(max_length=30, choices=VIOLATION_TYPES)
    description = models.TextField()
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'academic_violations'
        ordering = ['-detected_at']