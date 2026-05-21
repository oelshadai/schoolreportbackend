from django.contrib import admin
from .models import (
    School, AcademicYear, Term, Class, Subject, ClassSubject,
    GradingScale, SmsPurchaseOrder, Staff, StaffSalary, PayrollRecord,
    StaffPermission, Income, Expense, Budget, BudgetItem, ExpenseApproval, PaymentReminder,
    FinancialAuditLog
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
	list_display = ("name", "location", "phone_number", "email", "score_entry_mode", "show_student_photos", "show_promotion_on_terminal", "is_active")
	search_fields = ("name", "email", "location")
	list_filter = ("is_active", "score_entry_mode", "report_template")
	
	fieldsets = (
		('Basic Information', {
			'fields': ('name', 'address', 'location', 'phone_number', 'email', 'logo', 'motto', 'website')
		}),
		('System Configuration', {
			'fields': ('score_entry_mode', 'is_active', 'subscription_plan', 'subscription_expires'),
			'description': 'Configure how the system operates for this school'
		}),
		('Report Template Settings', {
			'fields': (
				'report_template', 
				'report_header_text', 
				'report_footer_text',
				'show_class_average',
				'show_position_in_class', 
				'show_attendance',
				'show_behavior_comments',
				'show_student_photos',
				'principal_signature',
				'show_headteacher_signature',
				'class_teacher_signature_required'
			),
			'description': 'Customize how report cards look and what information they include',
			'classes': ('collapse',)
		}),
		('Terminal Report Settings', {
			'fields': (
				'current_academic_year',
				'term_closing_date',
				'term_reopening_date',
				'show_promotion_on_terminal'
			),
			'description': 'Configure terminal report specific settings',
			'classes': ('collapse',)
		}),
		('Grade Scale', {
			'fields': (
				'grade_scale_a_min',
				'grade_scale_b_min', 
				'grade_scale_c_min',
				'grade_scale_d_min',
				'grade_scale_f_min'
			),
			'description': 'Set the minimum scores for each grade (A, B, C, D, F)',
			'classes': ('collapse',)
		}),
		('SMS Credits', {
			'fields': ('sms_balance',),
			'description': 'Current SMS unit balance. 1 unit = 1 SMS sent via the platform Arkesel account.',
		}),
	)


@admin.register(SmsPurchaseOrder)
class SmsPurchaseOrderAdmin(admin.ModelAdmin):
	list_display = ('school', 'sms_units', 'amount_ghs', 'status', 'requested_by', 'credited_at', 'created_at')
	list_filter = ('status', 'school')
	search_fields = ('school__name', 'paystack_reference')
	readonly_fields = ('school', 'requested_by', 'sms_units', 'amount_ghs', 'paystack_reference', 'credited_at', 'created_at', 'updated_at')
	ordering = ('-created_at',)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
	list_display = ("school", "name", "start_date", "end_date", "is_current")
	list_filter = ("school", "is_current")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
	list_display = ("academic_year", "name", "start_date", "end_date", "is_current")
	list_filter = ("name", "is_current")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
	list_display = ("school", "level", "section", "class_teacher", "capacity")
	list_filter = ("school", "level")
	search_fields = ("section",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
	list_display = ("name", "code", "category", "is_active")
	list_filter = ("category", "is_active")
	search_fields = ("name", "code")


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
	list_display = ("class_instance", "subject", "teacher")
	list_filter = ("class_instance", "subject")


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
	list_display = ("school", "grade", "min_score", "max_score", "remark")
	list_filter = ("school", "grade")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'first_name', 'last_name', 'position', 'status', 'school']
    list_filter = ['status', 'school', 'department']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email']


@admin.register(StaffPermission)
class StaffPermissionAdmin(admin.ModelAdmin):
    list_display = ['school', 'teacher', 'can_collect_fees', 'can_cover_attendance', 'can_manage_finances', 'created_at']
    list_filter = ['school', 'can_collect_fees', 'can_cover_attendance', 'can_manage_finances']
    search_fields = ['teacher__first_name', 'teacher__last_name', 'teacher__email']
    readonly_fields = ['created_at', 'updated_at']


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
