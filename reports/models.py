from django.db import models
from students.models import Student
from schools.models import Term


class ReportCard(models.Model):
    """Generated Report Card Model"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('GENERATED', 'Generated'),
        ('PUBLISHED', 'Published'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='report_cards')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='report_cards')
    
    # Report Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    pdf_file = models.FileField(upload_to='report_cards/', null=True, blank=True)
    # Use FileField initially to avoid Pillow requirement
    qr_code = models.FileField(upload_to='qr_codes/', null=True, blank=True)
    
    # Verification
    report_code = models.CharField(max_length=100, unique=True)
    
    # Metadata
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='generated_reports')
    generated_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_cards'
        unique_together = ['student', 'term']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report Card - {self.student.get_full_name()} - {self.term}"
    
    def generate_report_code(self):
        """Generate unique report verification code"""
        import uuid
        self.report_code = f"RC-{self.student.school.id}-{self.student.id}-{self.term.id}-{uuid.uuid4().hex[:8].upper()}"
        self.save()
