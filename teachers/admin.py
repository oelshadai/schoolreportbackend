from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id', 'get_full_name', 'get_email', 
        'is_class_teacher', 'experience_years', 'is_active', 'school'
    )
    list_filter = ('is_class_teacher', 'is_active', 'school', 'hire_date')
    search_fields = (
        'employee_id', 'user__first_name', 'user__last_name', 
        'user__email', 'qualification'
    )
    filter_horizontal = ('specializations',)
    readonly_fields = ('is_class_teacher', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id')
        }),
        ('School Information', {
            'fields': ('school', 'specializations')
        }),
        ('Employment Details', {
            'fields': ('hire_date', 'qualification', 'experience_years')
        }),
        ('Contact Information', {
            'fields': ('emergency_contact', 'address')
        }),
        ('Status', {
            'fields': ('is_class_teacher', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'