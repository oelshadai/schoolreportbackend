from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class School(models.Model):
    """School Model"""
    
    SCORE_ENTRY_MODES = [
        ('CLASS_TEACHER', 'Class Teacher Mode - Class teachers enter all subjects'),
        ('SUBJECT_TEACHER', 'Subject Teacher Mode - Subject teachers enter their own scores'),
    ]
    
    REPORT_TEMPLATES = [
        ('STANDARD', 'Standard Template'),
        ('DETAILED', 'Detailed Template with Comments'),
        ('COMPACT', 'Compact Template'),
        ('GHANA_EDUCATION_SERVICE', 'Ghana Education Service Template'),
        ('CUSTOM', 'Custom Template'),
    ]
    
    name = models.CharField(max_length=255)
    address = models.TextField()
    location = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    # Use FileField initially to avoid Pillow requirement; can switch to ImageField later
    logo = models.FileField(upload_to='school_logos/', null=True, blank=True)
    motto = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True, null=True)
    
    # Current academic year (for display purposes)
    current_academic_year = models.CharField(
        max_length=20,
        blank=True,
        help_text='Current academic year (e.g., 2024/2025)'
    )
    
    # Score entry configuration
    score_entry_mode = models.CharField(
        max_length=20, 
        choices=SCORE_ENTRY_MODES, 
        default='CLASS_TEACHER',
        help_text='Determines whether class teachers or subject teachers enter scores'
    )
    
    # Report template configuration
    report_template = models.CharField(
        max_length=30,
        choices=REPORT_TEMPLATES,
        default='STANDARD',
        help_text='Report card template style'
    )
    
    # Report customization
    report_header_text = models.TextField(
        blank=True,
        help_text='Custom header text for report cards (e.g., school vision/mission)'
    )
    report_footer_text = models.TextField(
        blank=True,
        help_text='Custom footer text for report cards (e.g., next term info)'
    )
    show_class_average = models.BooleanField(
        default=True,
        help_text='Show class average on report cards'
    )
    show_position_in_class = models.BooleanField(
        default=True,
        help_text='Show student position in class ranking'
    )
    show_attendance = models.BooleanField(
        default=True,
        help_text='Include attendance information on report cards'
    )
    show_behavior_comments = models.BooleanField(
        default=True,
        help_text='Include behavior/conduct comments'
    )
    principal_signature = models.FileField(
        upload_to='signatures/',
        null=True,
        blank=True,
        help_text='Principal signature image for report cards'
    )
    class_teacher_signature_required = models.BooleanField(
        default=False,
        help_text='Require class teacher signature on report cards'
    )
    show_student_photos = models.BooleanField(
        default=True,
        help_text='Show student photos on report cards'
    )
    show_headteacher_signature = models.BooleanField(
        default=True,
        help_text='Show headteacher signature section on report cards'
    )
    
    # Grade scale customization
    grade_scale_a_min = models.IntegerField(default=80, help_text='Minimum score for grade A')
    grade_scale_b_min = models.IntegerField(default=70, help_text='Minimum score for grade B')
    grade_scale_c_min = models.IntegerField(default=60, help_text='Minimum score for grade C')
    grade_scale_d_min = models.IntegerField(default=50, help_text='Minimum score for grade D')
    grade_scale_f_min = models.IntegerField(default=0, help_text='Minimum score for grade F')
    
    # Subscription
    is_active = models.BooleanField(default=True)
    subscription_plan = models.CharField(max_length=50, default='FREE')
    subscription_expires = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'schools'
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_grade_for_score(self, score):
        """Return grade letter for given score based on school's grade scale"""
        if score >= self.grade_scale_a_min:
            return 'A'
        elif score >= self.grade_scale_b_min:
            return 'B'
        elif score >= self.grade_scale_c_min:
            return 'C'
        elif score >= self.grade_scale_d_min:
            return 'D'
        else:
            return 'F'


class AcademicYear(models.Model):
    """Academic Year Model"""
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='academic_years')
    name = models.CharField(max_length=50)  # e.g., "2024/2025"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'academic_years'
        unique_together = ['school', 'name']
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Term(models.Model):
    """Term/Semester Model"""
    
    TERM_CHOICES = [
        ('FIRST', 'First Term'),
        ('SECOND', 'Second Term'),
        ('THIRD', 'Third Term'),
    ]
    
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=20, choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    total_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'terms'
        unique_together = ['academic_year', 'name']
        ordering = ['academic_year', 'name']
    
    def __str__(self):
        return f"{self.academic_year.name} - {self.get_name_display()}"


class Class(models.Model):
    """Class Model (Basic 1-9)"""
    
    LEVEL_CHOICES = [
        ('BASIC_1', 'Basic 1'),
        ('BASIC_2', 'Basic 2'),
        ('BASIC_3', 'Basic 3'),
        ('BASIC_4', 'Basic 4'),
        ('BASIC_5', 'Basic 5'),
        ('BASIC_6', 'Basic 6'),
        ('BASIC_7', 'Basic 7 (JHS 1)'),
        ('BASIC_8', 'Basic 8 (JHS 2)'),
        ('BASIC_9', 'Basic 9 (JHS 3)'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    section = models.CharField(max_length=10, blank=True)  # e.g., 'A', 'B', 'Gold', 'Diamond'
    class_teacher = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classes')
    capacity = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'classes'
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        unique_together = ['school', 'level', 'section']
        ordering = ['level', 'section']
    
    def __str__(self):
        if self.section:
            return f"{self.get_level_display()} {self.section}"
        return self.get_level_display()
    
    @property
    def full_name(self):
        return str(self)


class Subject(models.Model):
    """Subject Model"""
    
    CATEGORY_CHOICES = [
        ('PRIMARY', 'Primary (Basic 1-6)'),
        ('JHS', 'Junior High School (Basic 7-9)'),
        ('BOTH', 'Both Primary and JHS'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'subjects'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ClassSubject(models.Model):
    """Subject assigned to a specific class"""
    
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='class_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assigned_classes')
    teacher = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='teaching_subjects')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'class_subjects'
        unique_together = ['class_instance', 'subject']
        ordering = ['subject__name']
    
    def __str__(self):
        return f"{self.class_instance} - {self.subject.name}"


class GradingScale(models.Model):
    """Grading Scale Model"""
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='grading_scales')
    grade = models.CharField(max_length=5)  # A, B, C, D, E, F
    min_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    remark = models.CharField(max_length=50)  # Excellent, Very Good, Good, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'grading_scales'
        unique_together = ['school', 'grade']
        ordering = ['-min_score']
    
    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"
