from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from students.models import Student
from schools.models import ClassSubject, Class, Term


class Assignment(models.Model):
    """Assignment with workflow-aware validation"""
    
    ASSIGNMENT_TYPES = [
        ('HOMEWORK', 'Homework'),
        ('PROJECT', 'Project Work'),
        ('EXERCISE', 'Class Exercise'),
        ('QUIZ', 'Quiz'),
        ('EXAM', 'Exam'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PREVIEW', 'Preview'),
        ('PUBLISHED', 'Published'),
        ('CLOSED', 'Closed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='HOMEWORK')
    
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_assignments')
    
    attachment = models.FileField(upload_to='assignments/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])])
    
    start_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField()
    time_limit = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    max_score = models.IntegerField(default=10)
    max_attempts = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    is_timed = models.BooleanField(default=False)
    auto_grade = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    allow_file_submission = models.BooleanField(default=True)
    allow_text_submission = models.BooleanField(default=True)
    max_file_size = models.IntegerField(default=10)
    allowed_file_types = models.CharField(max_length=200, default='pdf,doc,docx,jpg,png,txt')
    
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments'
        ordering = ['-created_at']
    
    def clean(self):
        """Workflow-aware validation"""
        errors = {}
        
        # Skip validation for drafts
        if self.status == 'DRAFT':
            return
            
        # Teacher authorization
        if self.class_subject and self.created_by:
            if hasattr(self.class_subject, 'teacher') and self.class_subject.teacher != self.created_by:
                errors['class_subject'] = 'You do not teach this subject'
        
        # Published assignment requirements
        if self.status == 'PUBLISHED':
            if not self.class_subject:
                errors['class_subject'] = 'Subject required for published assignments'
            if not self.term:
                errors['term'] = 'Term required for published assignments'
            if not self.instructions.strip():
                errors['instructions'] = 'Instructions required for published assignments'
        
        # Type-specific validation
        if self.assignment_type == 'PROJECT' and not self.allow_file_submission:
            errors['allow_file_submission'] = 'Projects must allow file submission'
            
        if self.assignment_type in ['QUIZ', 'EXAM']:
            if not self.is_timed or not self.time_limit:
                errors['time_limit'] = f'{self.assignment_type} must have time limit'
                
        if self.assignment_type == 'EXAM' and self.max_attempts != 1:
            errors['max_attempts'] = 'Exams allow only 1 attempt'
        
        # Date validation
        if self.start_date and self.due_date and self.start_date >= self.due_date:
            errors['due_date'] = 'Due date must be after start date'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == 'PUBLISHED' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class StudentAssignment(models.Model):
    """Student assignment with attempt tracking"""
    
    SUBMISSION_STATUS = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
        ('LOCKED', 'Locked'),
        ('EXPIRED', 'Expired'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='student_assignments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignments')
    
    submission_text = models.TextField(blank=True)
    submission_file = models.FileField(upload_to='submissions/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])])
    
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    
    attempts_count = models.IntegerField(default=0)
    current_attempt_started_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS, default='NOT_STARTED')
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_assignments'
        unique_together = ['assignment', 'student']
        ordering = ['-created_at']
    
    def can_start_attempt(self):
        """Workflow-aware attempt validation"""
        if self.status in ['GRADED', 'LOCKED', 'EXPIRED']:
            return False, 'Assignment no longer available'
        
        if self.attempts_count >= self.assignment.max_attempts:
            return False, f'Maximum attempts ({self.assignment.max_attempts}) exceeded'
        
        if self.status == 'IN_PROGRESS' and self.current_attempt_started_at:
            if self.assignment.is_timed:
                elapsed = timezone.now() - self.current_attempt_started_at
                if elapsed.total_seconds() < (self.assignment.time_limit * 60):
                    return False, 'Attempt in progress'
        
        return True, 'Can start'
    
    def start_attempt(self):
        """Start new attempt with validation"""
        can_start, message = self.can_start_attempt()
        if not can_start:
            raise ValidationError(message)
        
        self.attempts_count += 1
        self.current_attempt_started_at = timezone.now()
        self.status = 'IN_PROGRESS'
        
        if self.assignment.assignment_type == 'EXAM':
            self.is_locked = True
        
        self.save()
    
    def submit(self, submission_data=None):
        """Submit with type-specific validation"""
        if self.assignment.assignment_type == 'PROJECT':
            if not self.submission_file and not (submission_data and submission_data.get('file')):
                raise ValidationError('Projects require file submission')
        
        self.status = 'SUBMITTED'
        self.submitted_at = timezone.now()
        self.is_locked = False
        self.save()


class Question(models.Model):
    """Quiz/exam questions with validation"""
    
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('short_answer', 'Short Answer'),
        ('project', 'Project/Practical'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='mcq')
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    expected_answer = models.TextField(blank=True)
    case_sensitive = models.BooleanField(default=False)
    word_limit = models.IntegerField(null=True, blank=True)
    
    allowed_file_types = models.JSONField(default=list, blank=True)
    max_file_size = models.IntegerField(default=10)
    max_files = models.IntegerField(default=5)
    
    is_required = models.BooleanField(default=True)
    explanation = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order', 'id']
    
    def clean(self):
        """Question validation"""
        if self.question_type == 'mcq' and not hasattr(self, 'options'):
            # Will be validated after options are created
            pass
        
        if self.question_type == 'short_answer' and not self.expected_answer.strip():
            raise ValidationError('Short answer questions need expected answer')
        
        if self.question_type == 'project' and not self.allowed_file_types:
            raise ValidationError('Project questions need allowed file types')


class QuestionOption(models.Model):
    """MCQ options"""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'question_options'
        ordering = ['order', 'id']


class QuizAttempt(models.Model):
    """Quiz attempt with time tracking"""
    
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
        ('EXPIRED', 'Expired'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='quiz_attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.IntegerField(null=True, blank=True)
    
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    class Meta:
        db_table = 'quiz_attempts'
        unique_together = ['assignment', 'student']
    
    @property
    def is_expired(self):
        if not self.assignment.is_timed or not self.assignment.time_limit:
            return False
        time_limit_seconds = self.assignment.time_limit * 60
        return (timezone.now() - self.started_at).total_seconds() > time_limit_seconds
    
    def calculate_score(self):
        """Calculate score from answers"""
        total_points = sum(answer.question.points for answer in self.answers.all())
        earned_points = sum(answer.points_earned for answer in self.answers.all())
        
        if total_points > 0:
            self.score = (earned_points / total_points) * self.assignment.max_score
        else:
            self.score = 0
        
        self.save()
        return self.score


class QuizAnswer(models.Model):
    """Student quiz answers"""
    
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, null=True, blank=True)
    answer_text = models.TextField(blank=True)
    answer_file = models.FileField(upload_to='answer_files/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])])
    
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    teacher_comment = models.TextField(blank=True)
    
    answered_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'quiz_answers'
        unique_together = ['attempt', 'question']
    
    def check_answer(self):
        """Auto-grade where possible"""
        if self.question.question_type == 'mcq':
            if self.selected_option and self.selected_option.is_correct:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        elif self.question.question_type == 'short_answer':
            expected = self.question.expected_answer.strip()
            student = self.answer_text.strip()
            
            if not self.question.case_sensitive:
                expected = expected.lower()
                student = student.lower()
            
            if expected == student:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        else:
            # Project questions need manual grading
            self.is_correct = None
            self.points_earned = 0
        
        self.save()


# Legacy models for backward compatibility
class AssignmentAttempt(models.Model):
    """Legacy attempt model"""
    student_assignment = models.ForeignKey(StudentAssignment, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.IntegerField()
    submission_text = models.TextField(blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, default='IN_PROGRESS')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'assignment_attempts'
        unique_together = ['student_assignment', 'attempt_number']


class StudentPortalAccess(models.Model):
    """Student portal credentials"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='portal_access')
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'student_portal_access'