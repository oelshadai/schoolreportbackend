from django.contrib import admin
from .models import School, AcademicYear, Term, Class, Subject, ClassSubject, GradingScale


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
	list_display = ("name", "location", "phone_number", "email", "score_entry_mode", "is_active")
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
				'principal_signature',
				'class_teacher_signature_required'
			),
			'description': 'Customize how report cards look and what information they include',
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
	)


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
