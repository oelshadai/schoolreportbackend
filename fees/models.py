from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from schools.models import School, Class
from django.contrib.auth import get_user_model

User = get_user_model()


class FeeType(models.Model):
    """Fee types/categories (Tuition, Canteen, Transport, etc.)"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_types')
    name = models.CharField(max_length=100)  # e.g., "Tuition", "Canteen", "Transport"
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('school', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.school.name}"


class FeeStructure(models.Model):
    """Fee amount per class/level and fee type"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_structures')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='structures')
    level = models.CharField(max_length=20)  # Class level (BASIC_1, BASIC_2, etc.)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    collection_period = models.CharField(
        max_length=20,
        choices=[
            ('TERM', 'Per Term'),
            ('YEAR', 'Per Year'),
            ('MONTH', 'Per Month'),
        ],
        default='TERM'
    )
    due_date = models.DateField(null=True, blank=True)  # Optional due date for this fee
    
    class Meta:
        unique_together = ('school', 'fee_type', 'level')
        ordering = ['fee_type', 'level']
    
    def __str__(self):
        return f"{self.fee_type.name} - {self.level}: {self.amount}"


class StudentFee(models.Model):
    """Student's fee record - total amount owed"""
    student = models.OneToOneField(
        'students.Student', 
        on_delete=models.CASCADE, 
        related_name='student_fee'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='student_fees')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    last_payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_STARTED', 'Not Started'),
            ('PARTIAL', 'Partially Paid'),
            ('PAID', 'Fully Paid'),
            ('DEFAULTED', 'Defaulted'),
        ],
        default='NOT_STARTED'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'school')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.student.student_id} - Balance: {self.balance}"


class FeePayment(models.Model):
    """Individual fee payment transaction"""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='fee_payments'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_payments')
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_date = models.DateTimeField(auto_now_add=True)
    collected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fee_collections',
        help_text='Admin or Class Teacher who collected the fee'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash'),
            ('CHEQUE', 'Cheque'),
            ('BANK_TRANSFER', 'Bank Transfer'),
            ('MOBILE_MONEY', 'Mobile Money'),
        ],
        default='CASH'
    )
    reference_number = models.CharField(max_length=100, blank=True)  # Receipt/Reference number
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_fee_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['school', 'payment_date']),
        ]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.fee_type.name}: {self.amount_paid}"


class FeeCollection(models.Model):
    """Fee collection session by teacher or admin"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_collections')
    collected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collection_sessions'
    )
    class_assigned = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Class if collected by class teacher, None if collected by admin'
    )
    collection_date = models.DateTimeField(auto_now_add=True)
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT)
    total_amount_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_students_paid = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-collection_date']
        indexes = [
            models.Index(fields=['collected_by', 'collection_date']),
            models.Index(fields=['school', 'collection_date']),
        ]
    
    def __str__(self):
        collector = self.collected_by.get_full_name() if self.collected_by else "Unknown"
        return f"{collector} - {self.fee_type.name} ({self.collection_date.date()})"
