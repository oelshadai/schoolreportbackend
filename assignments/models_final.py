# FINAL PRODUCTION STATE - After Migration Complete
# This shows what models.py should look like after all 3 phases

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
    
    # FINAL: Academic targeting - now required after migration
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    class_subject = models.ForeignKey(
        ClassSubject, 
        on_delete=models.CASCADE, 
        related_name='assignments',
        help_text='Subject is mandatory for academic categorization'
    )
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='assignments',
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
    
    # FINAL: Academic attempt control - now properly enforced
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
        # FINAL: Academic constraints implemented in clean() method
        # Database constraints removed to allow DRAFT → PUBLISHED workflow
        indexes = [
            models.Index(fields=['status', 'assignment_type']),
            models.Index(fields=['class_subject']),
            models.Index(fields=['term']),
        ]
    
    def clean(self):
        """PRODUCTION: Academic validation with workflow awareness"""
        from django.core.exceptions import ValidationError
        
        # Validate teacher owns the subject
        if self.class_subject and self.created_by:
            if self.class_subject.teacher != self.created_by:
                raise ValidationError('You do not teach this subject in this class')
        
        # WORKFLOW-AWARE ENFORCEMENT: Only validate when status requires it
        if self.status in ['PUBLISHED', 'ACTIVE']:
            # Type-specific validation for PUBLISHED assignments only
            if self.assignment_type == 'PROJECT' and not self.allow_file_submission:
                raise ValidationError('Projects must allow file submission')
            
            if self.assignment_type in ['QUIZ', 'EXAM']:
                if not self.is_timed or not self.time_limit:
                    raise ValidationError(f'{self.assignment_type} must have time limit')
            
            if self.assignment_type == 'EXAM' and self.max_attempts != 1:
                raise ValidationError('Exams allow only 1 attempt')
    
    def save(self, *args, **kwargs):
        # Only run full_clean for published assignments
        if self.status in ['PUBLISHED', 'ACTIVE']:
            self.full_clean()
        super().save(*args, **kwargs)