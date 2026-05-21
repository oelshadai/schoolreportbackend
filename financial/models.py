from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from schools.models import School
from decimal import Decimal
from datetime import datetime, date

User = get_user_model()


class Staff(models.Model):
    """School staff members for payroll"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ON_LEAVE', 'On Leave'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
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
        unique_together = ['school', 'staff_id']
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.staff_id})"


class StaffSalary(models.Model):
    """Salary structure for staff"""
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payrolls')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
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
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.category} - GH₵{self.amount} ({self.date})"


class Expense(models.Model):
    """Expense tracking"""
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
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_expenses')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    receipt_file = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
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
    
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount
    
    def utilization_percentage(self):
        if self.allocated_amount > 0:
            return (self.spent_amount / self.allocated_amount) * 100
        return 0
    
    def __str__(self):
        return f"{self.category} - GH₵{self.allocated_amount}"


class ExpenseApproval(models.Model):
    """Expense approval workflow"""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
        ordering = ['-reminder_date']
    
    def __str__(self):
        return f"Reminder for {self.staff} - {self.reminder_date}"


class FinancialAuditLog(models.Model):
    """Audit log for financial transactions and approval changes."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('PAY', 'Payment'),
        ('GENERATE', 'Generate'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_audit_logs')
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
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.model_name} {self.action} ({self.object_repr})"

    @staticmethod
    def _format_value(value):
        if isinstance(value, Decimal):
            return str(value)
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
                if value is not None:
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
