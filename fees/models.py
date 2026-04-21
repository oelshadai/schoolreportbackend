from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from schools.models import School, Class
from django.contrib.auth import get_user_model

User = get_user_model()


class FeeType(models.Model):
    """Fee types/categories (Tuition, Canteen, Transport, etc.)"""

    COLLECTION_FREQUENCY_CHOICES = [
        ('DAILY', 'Daily (Every School Day)'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('TERM', 'Per Term'),
        ('YEAR', 'Per Year'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_types')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Sub-fee hierarchy: if set, this FeeType is a sub-type of the parent
    parent_fee_type = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='sub_types',
        help_text='If set, this is a sub-fee type under the parent fee type.',
    )

    # When this fee is collected
    collection_frequency = models.CharField(
        max_length=10,
        choices=COLLECTION_FREQUENCY_CHOICES,
        default='TERM',
        help_text='How often this fee is charged'
    )
    # Day hint: for WEEKLY 0=Mon…6=Sun, for MONTHLY 1–31
    collection_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Day of month (1-31) for MONTHLY, or day of week (0=Mon, 6=Sun) for WEEKLY'
    )

    # Who is allowed to collect this fee type
    allow_class_teacher_collection = models.BooleanField(
        default=False,
        help_text='Class teachers may collect this fee for their own class'
    )
    allow_any_teacher_collection = models.BooleanField(
        default=False,
        help_text='Any teacher may collect this fee'
    )
    require_payment_approval = models.BooleanField(
        default=False,
        help_text='Each payment requires admin verification before it is finalised'
    )

    class Meta:
        unique_together = ('school', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class FeeStructure(models.Model):
    """Fee amount per class/level and fee type, with optional tier differentiation"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_structures')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='structures')
    level = models.CharField(max_length=20)  # Class level (BASIC_1, BASIC_2, etc.)
    tier_label = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Optional tier name (e.g. Bus Users, Non-Bus Users). Leave empty for all students.',
    )
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
        unique_together = ('school', 'fee_type', 'level', 'tier_label')
        ordering = ['fee_type', 'level', 'tier_label']
    
    def __str__(self):
        tier = f" [{self.tier_label}]" if self.tier_label else ""
        return f"{self.fee_type.name} - {self.level}{tier}: {self.amount}"


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
    # For DAILY fees auto-recorded from attendance: the actual school day this covers.
    # Used as the deduplication key so re-saving attendance never double-charges.
    attendance_date = models.DateField(
        null=True,
        blank=True,
        help_text='For daily fees auto-recorded from attendance; the school day this covers.',
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


class TermBill(models.Model):
    """
    Pre-generated fee bill for a student for a specific term and fee type.
    Used for TERM and YEAR frequency fees so students have a known amount
    to pay against. Daily/monthly fees are recorded directly as payments.
    """

    BILL_STATUS_CHOICES = [
        ('UNPAID', 'Not Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('WAIVED', 'Waived'),
    ]

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='term_bills'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='term_bills')
    term = models.ForeignKey(
        'schools.Term', on_delete=models.CASCADE, related_name='fee_bills'
    )
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name='term_bills')
    amount_billed = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=BILL_STATUS_CHOICES, default='UNPAID'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='generated_bills'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'term', 'fee_type')
        ordering = ['term', 'fee_type', 'student']

    def save(self, *args, **kwargs):
        self.balance = self.amount_billed - self.amount_paid
        if self.status != 'WAIVED':
            if self.amount_paid <= 0:
                self.status = 'UNPAID'
            elif self.balance > 0:
                self.status = 'PARTIAL'
            else:
                self.status = 'PAID'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.student_id} | {self.fee_type.name} | {self.term}"


class StudentFeeSubType(models.Model):
    """
    Assigns a student to a specific sub-fee type for a main fee type.

    Example:
        Main fee type:  Canteen Fee
        Sub-type A:     Bus Users Fee  (amount 100)
        Sub-type B:     Normal Fee     (amount 60)

    A student assigned to sub_fee_type=B will be billed GH₵60.
    Students with no assignment for a main fee type are not billed for that fee.
    """
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='fee_sub_type_assignments',
    )
    main_fee_type = models.ForeignKey(
        FeeType,
        on_delete=models.CASCADE,
        related_name='student_sub_assignments',
        help_text='The top-level (parent) fee type.',
    )
    sub_fee_type = models.ForeignKey(
        FeeType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_students',
        help_text='The sub-fee type assigned to this student. Null = none assigned.',
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='student_fee_sub_types')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'main_fee_type')
        ordering = ['student', 'main_fee_type']

    def __str__(self):
        sub = self.sub_fee_type.name if self.sub_fee_type else 'Unassigned'
        return f"{self.student.student_id} → {self.main_fee_type.name} [{sub}]"
