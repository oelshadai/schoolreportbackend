from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from students.models import Student
from schools.models import ClassSubject, Class, Term
from django.utils import timezone


class Assignment(models.Model):
    """Assignment created by teachers"""
    
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
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='HOMEWORK')
    
    # Assignment targeting
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assignments')
    
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
    time_limit = models.IntegerField(null=True, blank=True, help_text="Time limit in minutes for quiz/exam")
    max_score = models.IntegerField(default=10)
    
    # Quiz settings
    is_timed = models.BooleanField(default=False)
    auto_grade = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.class_instance}"
    
    @property
    def is_quiz_or_exam(self):
        return self.assignment_type in ['QUIZ', 'EXAM']


class StudentAssignment(models.Model):
    """Student's work on an assignment"""
    
    SUBMISSION_STATUS = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
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
    
    # Attempt tracking
    attempts_count = models.IntegerField(default=0, help_text="Number of times student has attempted this assignment")
    max_attempts = models.IntegerField(default=2, help_text="Maximum number of attempts allowed")
    
    # Status and timing
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS, default='NOT_STARTED')
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_assignments'
        unique_together = ['assignment', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.assignment.due_date < timezone.now() and self.status != 'SUBMITTED'
    
    @property
    def can_attempt(self):
        """Check if student can still attempt this assignment"""
        return self.attempts_count < self.max_attempts and self.status != 'GRADED'
    
    @property
    def attempts_remaining(self):
        """Get remaining attempts"""
        return max(0, self.max_attempts - self.attempts_count)


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
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('TRUE_FALSE', 'True/False'),
        ('SHORT_ANSWER', 'Short Answer'),
        ('ESSAY', 'Essay'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    # For short answer questions
    expected_answer = models.TextField(blank=True, help_text="Expected answer for short answer questions")
    case_sensitive = models.BooleanField(default=False, help_text="Whether answer matching is case sensitive")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."
    
    def check_short_answer(self, student_answer):
        """Check if student's short answer is correct"""
        if self.question_type != 'SHORT_ANSWER' or not self.expected_answer:
            return False
        
        expected = self.expected_answer.strip()
        student = student_answer.strip()
        
        if not self.case_sensitive:
            expected = expected.lower()
            student = student.lower()
        
        return expected == student


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
        """Auto-check answer for multiple choice, true/false, and short answer"""
        if self.question.question_type == 'MULTIPLE_CHOICE':
            if self.selected_option and self.selected_option.is_correct:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        elif self.question.question_type == 'TRUE_FALSE':
            correct_option = self.question.options.filter(is_correct=True).first()
            if self.selected_option and self.selected_option == correct_option:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        elif self.question.question_type == 'SHORT_ANSWER':
            if self.question.check_short_answer(self.answer_text):
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        
        self.save()