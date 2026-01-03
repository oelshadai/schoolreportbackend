from django.contrib import admin
from .models import Assignment, StudentAssignment, StudentPortalAccess


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'assignment_type', 'class_instance', 'class_subject', 'due_date', 'status', 'created_by']
    list_filter = ['assignment_type', 'status', 'class_instance', 'created_at']
    search_fields = ['title', 'description', 'created_by__first_name', 'created_by__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'assignment_type', 'status')
        }),
        ('Targeting', {
            'fields': ('class_instance', 'class_subject', 'term')
        }),
        ('Details', {
            'fields': ('due_date', 'max_score', 'attachment')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StudentAssignment)
class StudentAssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'status', 'score', 'submitted_at', 'graded_at']
    list_filter = ['status', 'assignment__assignment_type', 'submitted_at', 'graded_at']
    search_fields = ['student__first_name', 'student__last_name', 'assignment__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Assignment Info', {
            'fields': ('assignment', 'student', 'status')
        }),
        ('Submission', {
            'fields': ('submission_text', 'submission_file', 'submitted_at')
        }),
        ('Grading', {
            'fields': ('score', 'teacher_feedback', 'graded_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StudentPortalAccess)
class StudentPortalAccessAdmin(admin.ModelAdmin):
    list_display = ['student', 'username', 'is_active', 'last_login', 'created_at']
    list_filter = ['is_active', 'last_login', 'created_at']
    search_fields = ['student__first_name', 'student__last_name', 'username']
    readonly_fields = ['password_hash', 'created_at']
    
    fieldsets = (
        ('Student Info', {
            'fields': ('student', 'username', 'is_active')
        }),
        ('Access Info', {
            'fields': ('password_hash', 'last_login', 'created_at')
        })
    )