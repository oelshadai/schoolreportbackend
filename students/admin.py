from django.contrib import admin
from .models import Student, Attendance, Behaviour, StudentPromotion

# Register your models here.

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ("student_id", "first_name", "last_name", "gender", "current_class", "is_active")
	search_fields = ("student_id", "first_name", "last_name")
	list_filter = ("gender", "is_active", "current_class")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
	list_display = ("student", "term", "days_present", "days_absent", "times_late")
	list_filter = ("term",)

@admin.register(Behaviour)
class BehaviourAdmin(admin.ModelAdmin):
	list_display = ("student", "term", "conduct", "attitude", "interest", "punctuality")
	list_filter = ("term", "conduct")

@admin.register(StudentPromotion)
class StudentPromotionAdmin(admin.ModelAdmin):
	list_display = ("student", "from_class", "to_class", "academic_year", "promoted_date", "is_graduated")
	list_filter = ("academic_year", "is_graduated")
