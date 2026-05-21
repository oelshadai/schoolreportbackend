from django.contrib import admin
from .models import (
    Staff, StaffSalary, PayrollRecord, Income, Expense,
    Budget, BudgetItem, ExpenseApproval, PaymentReminder,
    FinancialAuditLog
)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'first_name', 'last_name', 'position', 'status', 'school']
    list_filter = ['status', 'school', 'department']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email']


@admin.register(StaffSalary)
class StaffSalaryAdmin(admin.ModelAdmin):
    list_display = ['staff', 'basic_salary', 'net_salary', 'effective_date', 'is_active']
    list_filter = ['is_active', 'effective_date']
    search_fields = ['staff__first_name', 'staff__last_name']


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ['staff', 'month', 'year', 'net_salary', 'status', 'payment_date']
    list_filter = ['status', 'year', 'month', 'school']
    search_fields = ['staff__first_name', 'staff__last_name']


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'date', 'received_from', 'school']
    list_filter = ['category', 'date', 'school']
    search_fields = ['description', 'received_from']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'date', 'status', 'paid_to', 'school']
    list_filter = ['category', 'status', 'date', 'school']
    search_fields = ['description', 'paid_to']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'total_amount', 'is_active', 'school']
    list_filter = ['is_active', 'start_date', 'school']
    search_fields = ['name', 'description']


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ['budget', 'category', 'allocated_amount', 'spent_amount', 'remaining_amount']
    list_filter = ['budget']
    search_fields = ['category', 'description']


@admin.register(ExpenseApproval)
class ExpenseApprovalAdmin(admin.ModelAdmin):
    list_display = ['expense', 'approver', 'status', 'created_at']
    list_filter = ['status', 'created_at']


@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ['staff', 'reminder_date', 'is_sent', 'sent_at']
    list_filter = ['is_sent', 'reminder_date']


@admin.register(FinancialAuditLog)
class FinancialAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'model_name', 'action', 'object_repr', 'user', 'school']
    list_filter = ['model_name', 'action', 'timestamp', 'school']
    search_fields = ['object_repr', 'notes', 'changes']
