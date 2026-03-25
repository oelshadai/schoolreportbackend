from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from students.models import Student
from schools.models import ClassSubject, Class, Term


class Assignment(models.Model):
    """Assignment created by teachers with academic enforcement"""
    
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
    instructions = models.TextField(help_text="Detailed instructions are required for academic clarity")
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='HOMEWORK')
    
    # TRANSITIONAL: Academic targeting - nullable during migration
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    class_subject = models.ForeignKey(
        ClassSubject, 
        on_delete=models.CASCADE, 
        related_name='assignments',
        null=True, blank=True,  # TRANSITIONAL: Will be required after data migration
        help_text='Subject is mandatory for academic categorization'
    )
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='assignments',
        null=True, blank=True,  # TRANSITIONAL: Will be required after data migration
        help_text='Academic term for this assignment'
    )
    
    # Teacher who created it
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_assignments')
    
    # Files and resources
    attachment = models.FileField(
        upload_to='assignments/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])]
    )
    
    # Timing
    start_date = models.DateTimeField(null=True, blank=True, help_text="When assignment becomes available")
    due_date = models.DateTimeField()
    time_limit = models.IntegerField(
        null=True, blank=True, 
        help_text="Time limit in minutes for quiz/exam",
        validators=[MinValueValidator(1)]
    )
    max_score = models.IntegerField(default=10)
    
    # TRANSITIONAL: Academic attempt control - safe defaults
    max_attempts = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Maximum submission attempts allowed'
    )
    
    # Quiz settings
    is_timed = models.BooleanField(default=False)
    auto_grade = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Enhanced fields
    instructions_file = models.FileField(
        upload_to='assignment_instructions/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    allow_file_submission = models.BooleanField(default=True)
    allow_text_submission = models.BooleanField(default=True)
    max_file_size = models.IntegerField(default=10, help_text="Maximum file size in MB")
    allowed_file_types = models.CharField(
        max_length=200, 
        default='pdf,doc,docx,jpg,png,txt',
        help_text="Comma-separated file extensions"
    )
    
    published_at = models.DateTimeField(null=True, blank=True)
    previewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments'
        ordering = ['-created_at']
        # TRANSITIONAL: No database constraints during migration
        # Will be added in Phase 3 after data migration
    
    def clean(self):
        """PRODUCTION-SAFE: Academic validation with workflow awareness"""
        from django.core.exceptions import ValidationError
        
        # TRANSITIONAL: Skip validation if fields are still being migrated
        if not hasattr(self, 'class_subject') or not hasattr(self, 'term'):
            return
            
        # Validate teacher owns the subject (if class_subject exists)
        if self.class_subject and self.created_by:
            if self.class_subject.teacher != self.created_by:
                raise ValidationError('You do not teach this subject in this class')
        
        # WORKFLOW-AWARE ENFORCEMENT: Only validate when status requires it
        if self.status in ['PUBLISHED', 'ACTIVE']:
            # Require class_subject for published assignments
            if not self.class_subject:
                raise ValidationError('Subject assignment is required for published assignments')
                
            # Require term for published assignments
            if not self.term:
                raise ValidationError('Term is required for published assignments')
                
            # Type-specific validation for ACTIVE assignments only
            if self.assignment_type == 'PROJECT' and not self.allow_file_submission:
                raise ValidationError('Projects must allow file submission')
            
            if self.assignment_type in ['QUIZ', 'EXAM']:
                if not self.is_timed or not self.time_limit:
                    raise ValidationError(f'{self.assignment_type} must have time limit')
            
            if self.assignment_type == 'EXAM' and self.max_attempts != 1:
                raise ValidationError('Exams allow only 1 attempt')
    
    def save(self, *args, **kwargs):
        # Skip validation if explicitly requested or if it's a draft
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation and self.status not in ['DRAFT', 'PREVIEW']:
            self.full_clean()
        super().save(*args, **kwargs)


class StudentAssignment(models.Model):
    """Student's work on an assignment with academic enforcement"""
    
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
    
    # Student's work
    submission_text = models.TextField(blank=True)
    submission_file = models.FileField(
        upload_to='submissions/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])]
    )
    
    # Grading
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    
    # Academic attempt tracking
    attempts_count = models.IntegerField(default=0, help_text="Number of attempts made")
    current_attempt_started_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False, help_text="Locked during timed attempts")
    
    # Status and timing
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS, default='NOT_STARTED')
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    additional_files = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_assignments'
        unique_together = ['assignment', 'student']
        ordering = ['-created_at']
    
    def can_start_attempt(self):
        """Check if student can start new attempt"""
        if self.status in ['GRADED', 'LOCKED', 'EXPIRED']:
            return False, 'Assignment is no longer available'
        
        if self.attempts_count >= self.assignment.max_attempts:
            return False, f'Maximum attempts ({self.assignment.max_attempts}) exceeded'
        
        # Check if currently in progress
        if self.status == 'IN_PROGRESS' and self.current_attempt_started_at:
            if self.assignment.is_timed:
                elapsed = timezone.now() - self.current_attempt_started_at
                if elapsed.total_seconds() < (self.assignment.time_limit * 60):
                    return False, 'Attempt already in progress'
        
        return True, 'Can start attempt'
    
    def start_attempt(self):
        """Start new attempt with academic enforcement"""
        can_start, message = self.can_start_attempt()
        if not can_start:
            raise ValidationError(message)
        
        self.attempts_count += 1
        self.current_attempt_started_at = timezone.now()
        self.status = 'IN_PROGRESS'
        
        # Lock for exams
        if self.assignment.assignment_type == 'EXAM':
            self.is_locked = True
        
        self.save()
    
    def check_time_limit(self):
        """Check if time limit exceeded"""
        if not self.assignment.is_timed or not self.current_attempt_started_at:
            return False
        
        elapsed = timezone.now() - self.current_attempt_started_at
        return elapsed.total_seconds() > (self.assignment.time_limit * 60)
    
    def auto_submit_if_expired(self):
        """Auto-submit if time limit exceeded"""
        if self.check_time_limit() and self.status == 'IN_PROGRESS':
            self.status = 'EXPIRED'
            self.submitted_at = timezone.now()
            self.is_locked = False
            self.save()
            return True
        return False
    
    def submit(self, submission_data=None):
        """Submit assignment with academic validation"""
        from django.core.exceptions import ValidationError
        
        # Check if expired
        if self.auto_submit_if_expired():
            raise ValidationError('Time limit exceeded - assignment auto-submitted')
        
        # Validate submission based on type
        if self.assignment.assignment_type == 'PROJECT':
            if not self.submission_file and not (submission_data and submission_data.get('file')):
                raise ValidationError('Projects require file submission')
        
        if self.assignment.assignment_type in ['QUIZ', 'EXAM']:
            if not submission_data or not submission_data.get('answers'):
                raise ValidationError('Quiz/Exam requires answers')
        
        self.status = 'SUBMITTED'
        self.submitted_at = timezone.now()
        self.is_locked = False
        self.save()


class AssignmentAttempt(models.Model):
    """Individual attempt at an assignment with history"""
    
    ATTEMPT_STATUS = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
        ('ABANDONED', 'Abandoned'),
    ]
    
    student_assignment = models.ForeignKey(StudentAssignment, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.IntegerField(help_text="Which attempt this is (1, 2, etc.)")
    
    # Attempt data
    submission_text = models.TextField(blank=True)
    submission_file = models.FileField(
        upload_to='attempt_submissions/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])]
    )
    
    # Grading for this attempt
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    
    # Status and timing
    status = models.CharField(max_length=20, choices=ATTEMPT_STATUS, default='IN_PROGRESS')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # From migration 0006
    additional_files = models.JSONField(default=list, blank=True, help_text="List of additional file URLs")
    time_spent = models.IntegerField(default=0, help_text="Time spent in seconds")
    
    class Meta:
        db_table = 'assignment_attempts'
        unique_together = ['student_assignment', 'attempt_number']
        ordering = ['-attempt_number']
    
    def __str__(self):
        return f"{self.student_assignment.student.get_full_name()} - {self.student_assignment.assignment.title} (Attempt {self.attempt_number})"


class StudentPortalAccess(models.Model):
    """Student portal access credentials"""
    
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='portal_access')
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'student_portal_access'
    
    def __str__(self):
        return f"Portal: {self.student.get_full_name()}"


class Question(models.Model):
    """Questions for quiz/exam assignments"""
    
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
    
    # For short answer questions - from migration 0008
    expected_answer = models.TextField(blank=True, help_text="Expected answer for short answer questions")
    case_sensitive = models.BooleanField(default=False, help_text="Whether answer matching is case sensitive")
    word_limit = models.IntegerField(null=True, blank=True, help_text="Maximum word count for short answer")
    character_limit = models.IntegerField(null=True, blank=True, help_text="Maximum character count for short answer")
    
    # For project questions - from migration 0008
    allowed_file_types = models.JSONField(default=list, blank=True, help_text="List of allowed file extensions")
    max_file_size = models.IntegerField(default=10, help_text="Maximum file size in MB")
    max_files = models.IntegerField(default=5, help_text="Maximum number of files allowed")
    
    # From migration 0006
    question_image = models.ImageField(upload_to='question_images/', null=True, blank=True)
    question_file = models.FileField(
        upload_to='question_files/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt'])]
    )
    is_required = models.BooleanField(default=True)
    explanation = models.TextField(blank=True, help_text="Explanation shown after answering")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."
    
    def check_short_answer(self, student_answer):
        """Check if student's short answer is correct"""
        if self.question_type != 'short_answer' or not self.expected_answer:
            return False
        
        expected = self.expected_answer.strip()
        student = student_answer.strip()
        
        if not self.case_sensitive:
            expected = expected.lower()
            student = student.lower()
        
        return expected == student
    
    def validate_file_upload(self, file):
        """Validate uploaded file for project questions"""
        if self.question_type != 'project':
            return True, "Not a project question"
        
        if not file:
            return False, "No file uploaded"
        
        # Check file size
        if file.size > self.max_file_size * 1024 * 1024:  # Convert MB to bytes
            return False, f"File size exceeds {self.max_file_size}MB limit"
        
        # Check file type
        if self.allowed_file_types:
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in [ext.lower() for ext in self.allowed_file_types]:
                return False, f"File type .{file_ext} not allowed. Allowed types: {', '.join(self.allowed_file_types)}"
        
        return True, "File is valid"


class QuestionOption(models.Model):
    """Options for multiple choice questions"""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'question_options'
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.option_text} ({'✓' if self.is_correct else '✗'})"


class TimedTask(models.Model):
    """Timed task with specific start time and duration"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SCHEDULED', 'Scheduled'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    class_instance = models.ForeignKey('schools.Class', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    start_time = models.DateTimeField(help_text="When students can start the task")
    duration = models.IntegerField(help_text="Duration in minutes")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'timed_tasks'
    
    def __str__(self):
        return f"{self.title} - {self.class_instance}"
    
    @property
    def is_active(self):
        now = timezone.now()
        end_time = self.start_time + timezone.timedelta(minutes=self.duration)
        return self.start_time <= now <= end_time and self.status == 'ACTIVE'
    
    @property
    def can_start(self):
        return timezone.now() >= self.start_time and self.status == 'ACTIVE'


class TaskQuestion(models.Model):
    """Questions for timed tasks"""
    
    task = models.ForeignKey(TimedTask, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_answer = models.IntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')])
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'task_questions'
        ordering = ['order']
    
    @property
    def options(self):
        return [self.option_a, self.option_b, self.option_c, self.option_d]


class TaskAttempt(models.Model):
    """Student's attempt at a timed task"""
    
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('AUTO_SUBMITTED', 'Auto Submitted'),
        ('EXPIRED', 'Expired'),
    ]
    
    task = models.ForeignKey(TimedTask, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='task_attempts')
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.IntegerField(null=True, blank=True, help_text="Time taken in seconds")
    
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    class Meta:
        db_table = 'task_attempts'
        unique_together = ['task', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.task.title}"
    
    @property
    def time_remaining(self):
        if self.status != 'IN_PROGRESS':
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = (self.task.duration * 60) - elapsed
        return max(0, int(remaining))
    
    def auto_submit(self):
        """Auto-submit when time expires"""
        if self.status == 'IN_PROGRESS':
            self.status = 'AUTO_SUBMITTED'
            self.submitted_at = timezone.now()
            self.time_taken = self.task.duration * 60
            self.calculate_score()
            self.save()
    
    def calculate_score(self):
        """Calculate score based on answers"""
        total_questions = self.task.questions.count()
        if total_questions == 0:
            self.score = 0
            return
        
        correct_answers = 0
        for answer in self.answers.all():
            if answer.is_correct:
                correct_answers += 1
        
        self.score = (correct_answers / total_questions) * 100
        self.save()


class TaskAnswer(models.Model):
    """Student's answer to a task question"""
    
    attempt = models.ForeignKey(TaskAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(TaskQuestion, on_delete=models.CASCADE)
    selected_option = models.IntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')])
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_answers'
        unique_together = ['attempt', 'question']
    
    def save(self, *args, **kwargs):
        self.is_correct = self.selected_option == self.question.correct_answer
        super().save(*args, **kwargs)


class QuizAttempt(models.Model):
    """Student's attempt at a quiz/exam"""
    
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
    time_taken = models.IntegerField(null=True, blank=True, help_text="Time taken in seconds")
    
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    class Meta:
        db_table = 'quiz_attempts'
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"
    
    @property
    def is_expired(self):
        if not self.assignment.is_timed or not self.assignment.time_limit:
            return False
        time_limit_seconds = self.assignment.time_limit * 60
        return (timezone.now() - self.started_at).total_seconds() > time_limit_seconds
    
    def calculate_score(self):
        """Calculate score based on answers"""
        total_points = 0
        earned_points = 0
        
        for answer in self.answers.all():
            total_points += answer.question.points
            if answer.is_correct:
                earned_points += answer.question.points
        
        if total_points > 0:
            self.score = (earned_points / total_points) * self.assignment.max_score
        else:
            self.score = 0
        
        self.save()
        return self.score


class QuizAnswer(models.Model):
    """Student's answer to a quiz question"""
    
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For multiple choice
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, null=True, blank=True)
    
    # For text answers
    answer_text = models.TextField(blank=True)
    
    # For file uploads (project questions) - LEGACY: Keep during transition
    answer_files = models.JSONField(default=list, blank=True, help_text="List of uploaded file paths - DEPRECATED")
    
    # From migration 0006
    answer_file = models.FileField(
        upload_to='answer_files/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])]
    )
    teacher_comment = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # Grading
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'quiz_answers'
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.student.get_full_name()} - Q{self.question.order}"
    
    def check_answer(self):
        """Auto-check answer for multiple choice and short answer"""
        if self.question.question_type == 'mcq':
            if self.selected_option and self.selected_option.is_correct:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        elif self.question.question_type == 'short_answer':
            if self.question.check_short_answer(self.answer_text):
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        elif self.question.question_type == 'project':
            # Project questions require manual grading
            self.is_correct = None  # Pending manual review
            self.points_earned = 0
        
        self.save()


class SubmissionFile(models.Model):
    """File submissions for assignments - from migration 0006"""
    
    student_assignment = models.ForeignKey(StudentAssignment, on_delete=models.CASCADE, related_name='files')
    attempt = models.ForeignKey(AssignmentAttempt, on_delete=models.CASCADE, related_name='files', null=True, blank=True)
    
    file = models.FileField(
        upload_to='submission_files/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt', 'zip'])]
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'submission_files'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.student_assignment}"


class QuestionFile(models.Model):
    """File answers for quiz questions - from migration 0006"""
    
    answer = models.ForeignKey(QuizAnswer, on_delete=models.CASCADE, related_name='files')
    
    file = models.FileField(
        upload_to='answer_files/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'])]
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'question_files'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.answer}"


# NEW ADDITIVE MODEL - QuizAnswerFile for professional file uploads
class QuizAnswerFile(models.Model):
    """
    Professional per-question file uploads for project questions.
    ADDITIVE ONLY - does not replace legacy answer_files JSONField.
    """
    quiz_answer = models.ForeignKey(
        QuizAnswer,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )

    file = models.FileField(
        upload_to='quiz_submissions/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf','doc','docx','jpg','jpeg','png','txt','zip']
            )
        ]
    )

    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_answer_files'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.original_filename} - {self.quiz_answer.question.question_text[:30]}..."

    def save(self, *args, **kwargs):
        import mimetypes
        if self.file:
            self.file_size = self.file.size
            self.mime_type = mimetypes.guess_type(self.original_filename or self.file.name)[0] or 'application/octet-stream'
        super().save(*args, **kwargs)