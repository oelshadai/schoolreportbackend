from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, date


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
    
    # Current term
    current_term = models.ForeignKey(
        'Term',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools_using_as_current',
        help_text='Currently active term for the school'
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
    
    # Terminal Report Settings
    term_closing_date = models.DateField(
        null=True, 
        blank=True,
        help_text='Term closing date to appear on terminal reports'
    )
    term_reopening_date = models.DateField(
        null=True, 
        blank=True,
        help_text='Term reopening date to appear on terminal reports'
    )
    show_promotion_on_terminal = models.BooleanField(
        default=True,
        help_text='Show promotion status on terminal reports'
    )
    
    # Subscription
    is_active = models.BooleanField(default=True)
    subscription_plan = models.CharField(max_length=50, default='FREE')
    subscription_expires = models.DateField(null=True, blank=True)

    # Staff Permissions
    special_fee_collection_enabled = models.BooleanField(
        default=True,
        help_text='Master switch — when off, no special fee-collector teacher can see the fee collection page'
    )

    # Teacher student management
    teachers_can_add_students = models.BooleanField(
        default=True,
        help_text='Master switch — when off, class teachers cannot add students; only admins can'
    )

    # ---------------------------------------------------------------
    # Parent Portal Settings
    # ---------------------------------------------------------------
    parent_portal_enabled = models.BooleanField(
        default=False,
        help_text='Master switch — when off, no parent can log in'
    )
    parent_can_view_grades = models.BooleanField(default=True)
    parent_can_view_attendance = models.BooleanField(default=True)
    parent_can_view_fees = models.BooleanField(default=True)
    parent_can_view_reports = models.BooleanField(default=True)
    parent_can_pay_fees_online = models.BooleanField(
        default=False,
        help_text='Allow parents to initiate online fee payments via Paystack'
    )
    parent_can_message_teachers = models.BooleanField(default=False)
    parent_support_email = models.EmailField(blank=True, default='')
    paystack_public_key = models.CharField(
        max_length=100, blank=True,
        help_text='Your Paystack public key (pk_live_... or pk_test_...)'
    )
    paystack_secret_key = models.CharField(
        max_length=100, blank=True,
        help_text='Your Paystack secret key — kept server-side only'
    )

    # ---------------------------------------------------------------
    # SMS / Notifications Settings (Arkesel)
    # ---------------------------------------------------------------
    sms_enabled = models.BooleanField(
        default=False,
        help_text='Master switch — enable SMS notifications for this school'
    )
    arkesel_api_key = models.CharField(
        max_length=200, blank=True,
        help_text='Arkesel API key from your Arkesel dashboard'
    )
    sms_sender_name = models.CharField(
        max_length=11, blank=True, default='SchoolSMS',
        help_text='SMS sender ID (max 11 alphanumeric chars, e.g. "MySchool")'
    )
    sms_attendance_enabled = models.BooleanField(
        default=False,
        help_text='Send SMS to parents/guardians when attendance is taken'
    )
    sms_fee_reminder_enabled = models.BooleanField(
        default=False,
        help_text='Allow admins to send fee-reminder SMS to parents of students with unpaid bills'
    )

    # SMS credit balance — number of SMS units this school has purchased
    sms_balance = models.PositiveIntegerField(
        default=0,
        help_text='Number of SMS units available (1 unit = 1 SMS sent via the platform Arkesel account)'
    )

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


class SmsPurchaseOrder(models.Model):
    """Tracks SMS credit purchase orders made by schools via Paystack."""

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Payment'),
        (STATUS_PAID, 'Paid — Credited'),
        (STATUS_FAILED, 'Payment Failed'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='sms_purchases'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sms_purchase_orders'
    )
    sms_units = models.PositiveIntegerField(help_text='Number of SMS credits purchased')
    amount_ghs = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount paid in GHS')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    paystack_reference = models.CharField(max_length=100, blank=True, unique=True, null=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sms_purchase_orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name} — {self.sms_units} SMS — {self.status}"


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
    class_teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classes')
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
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='teaching_subjects')
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


class StaffPermission(models.Model):
    """
    Grants a teacher extra cross-class permissions:
    - can_collect_fees: teacher appears as a special fee collector
    - fee_collection_enabled: sub-toggle; admin flips this off/on without deleting the record
    - collect_fee_types: specific fee types they handle (empty = all allowed types)
    - can_cover_attendance: teacher can take attendance for other classes
    - cover_classes: which classes they cover (empty = all, but only when can_cover_attendance=True)
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='staff_permissions')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='staff_permissions',
        limit_choices_to={'role': 'TEACHER'},
    )

    # Fee collection
    can_collect_fees = models.BooleanField(default=False)
    fee_collection_enabled = models.BooleanField(
        default=True,
        help_text='Sub-toggle: turn off to hide fee collection from this teacher without removing the assignment',
    )
    collect_fee_types = models.ManyToManyField(
        'fees.FeeType', blank=True, related_name='special_collectors',
        help_text='Leave empty to allow all active fee types',
    )

    # Attendance cover
    can_cover_attendance = models.BooleanField(default=False)
    cover_classes = models.ManyToManyField(
        'schools.Class', blank=True, related_name='cover_teachers',
        help_text='Classes this teacher can cover for attendance',
    )

    # Financial management
    can_manage_finances = models.BooleanField(
        default=False,
        help_text='Allow this staff member to access financial management (bursar role)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_permissions'
        unique_together = ('school', 'teacher')
        verbose_name = 'Staff Permission'

    def __str__(self):
        return f"{self.teacher.get_full_name()} — {self.school.name}"


# ============================================================================
# FINANCIAL MANAGEMENT MODELS
# ============================================================================

class Staff(models.Model):
    """School staff members for payroll management"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ON_LEAVE', 'On Leave'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    staff_id = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_staff'
        unique_together = ['school', 'staff_id']
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.staff_id})"


class StaffSalary(models.Model):
    """Salary structure for staff members"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salaries')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pension_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_date = models.DateField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_staffsalary'
        ordering = ['-effective_date']
    
    def gross_salary(self):
        return (self.basic_salary + self.housing_allowance + 
                self.transport_allowance + self.other_allowances)
    
    def total_deductions(self):
        return (self.tax_deduction + self.pension_deduction + 
                self.other_deductions)
    
    def net_salary(self):
        return self.gross_salary() - self.total_deductions()
    
    def __str__(self):
        return f"{self.staff} - GH₵{self.net_salary()}"


class PayrollRecord(models.Model):
    """Monthly payroll records"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='payroll_records')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='payroll_records')
    salary = models.ForeignKey(StaffSalary, on_delete=models.SET_NULL, null=True)
    month = models.IntegerField()
    year = models.IntegerField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_payrolls')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_payrollrecord'
        unique_together = ['school', 'staff', 'month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.staff} - {self.month}/{self.year}"


class Income(models.Model):
    """Income tracking"""
    CATEGORY_CHOICES = [
        ('TUITION', 'Tuition Fees'),
        ('REGISTRATION', 'Registration Fees'),
        ('EXAM', 'Examination Fees'),
        ('TRANSPORT', 'Transport Fees'),
        ('CANTEEN', 'Canteen Fees'),
        ('DONATION', 'Donations'),
        ('GRANT', 'Grants'),
        ('OTHER', 'Other Income'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='incomes')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date = models.DateField()
    received_from = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_income'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.category} - GH₵{self.amount} ({self.date})"


class Expense(models.Model):
    """Expense tracking with approval workflow"""
    CATEGORY_CHOICES = [
        ('SALARY', 'Salaries'),
        ('UTILITIES', 'Utilities'),
        ('MAINTENANCE', 'Maintenance'),
        ('SUPPLIES', 'Supplies'),
        ('TRANSPORT', 'Transport'),
        ('EQUIPMENT', 'Equipment'),
        ('TRAINING', 'Training'),
        ('MARKETING', 'Marketing'),
        ('OTHER', 'Other Expenses'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='expenses')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date = models.DateField()
    paid_to = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='requested_expenses')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    receipt_file = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_expense'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.category} - GH₵{self.amount} ({self.date})"


class Budget(models.Model):
    """Annual/Term budget planning"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_budget'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class BudgetItem(models.Model):
    """Budget line items"""
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=100)
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'financial_budgetitem'
    
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount
    
    def utilization_percentage(self):
        if self.allocated_amount > 0:
            return (self.spent_amount / self.allocated_amount) * 100
        return 0
    
    def __str__(self):
        return f"{self.category} - GH₵{self.allocated_amount}"


class ExpenseApproval(models.Model):
    """Expense approval workflow tracking"""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_expenseapproval'
    
    def __str__(self):
        return f"{self.expense} - {self.status}"


class PaymentReminder(models.Model):
    """Salary payment reminders"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='payment_reminders')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='payment_reminders')
    payroll = models.ForeignKey(PayrollRecord, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateField()
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'financial_paymentreminder'
        ordering = ['-reminder_date']
    
    def __str__(self):
        return f"Reminder for {self.staff} - {self.reminder_date}"


class FinancialAuditLog(models.Model):
    """Audit trail for financial changes and approvals."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('PAY', 'Payment'),
        ('GENERATE', 'Generate'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='financial_audit_logs', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_audit_logs')
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changes = models.JSONField(default=dict, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'financial_auditlog'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.model_name} {self.action} ({self.object_repr})"

    @staticmethod
    def _format_value(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, '__str__') and not isinstance(value, (dict, list, tuple)):
            return str(value)
        return value

    @classmethod
    def serialize_instance(cls, instance):
        data = {}
        for field in instance._meta.fields:
            if field.name in ('created_at', 'updated_at'):
                continue
            if field.auto_created and not field.concrete:
                continue
            try:
                value = getattr(instance, field.name)
            except Exception:
                continue
            if hasattr(field, 'related_model') and field.related_model is not None:
                value = getattr(value, 'pk', value)
            data[field.name] = cls._format_value(value)
        return data

    @classmethod
    def compute_changes(cls, old_data, new_data):
        changes = {}
        for key, new_value in new_data.items():
            old_value = old_data.get(key)
            if old_value != new_value:
                changes[key] = {'from': old_value, 'to': new_value}
        return changes

    @classmethod
    def resolve_school(cls, instance):
        if hasattr(instance, 'school') and instance.school is not None:
            return instance.school
        if hasattr(instance, 'staff') and getattr(instance.staff, 'school', None) is not None:
            return instance.staff.school
        if hasattr(instance, 'budget') and getattr(instance.budget, 'school', None) is not None:
            return instance.budget.school
        return None

    @classmethod
    def log_action(cls, instance, user=None, action='UPDATE', changes=None, extra_data=None, notes=''):
        if instance is None:
            return None

        content_type = ContentType.objects.get_for_model(instance.__class__)
        school = cls.resolve_school(instance)
        object_id = str(getattr(instance, 'pk', ''))

        if changes is None:
            changes = cls.serialize_instance(instance)

        return cls.objects.create(
            school=school,
            user=user,
            content_type=content_type,
            object_id=object_id,
            object_repr=str(instance),
            model_name=instance._meta.model_name,
            action=action,
            changes=changes,
            extra_data=extra_data or {},
            notes=notes,
        )
