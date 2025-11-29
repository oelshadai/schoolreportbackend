from django.contrib import admin
from .models import ContinuousAssessment, ExamScore, SubjectResult, TermResult


@admin.register(ContinuousAssessment)
class ContinuousAssessmentAdmin(admin.ModelAdmin):
	list_display = ("student", "class_subject", "term", "total_ca_score")
	list_filter = ("term", "class_subject")


@admin.register(ExamScore)
class ExamScoreAdmin(admin.ModelAdmin):
	list_display = ("student", "class_subject", "term", "score")
	list_filter = ("term", "class_subject")


@admin.register(SubjectResult)
class SubjectResultAdmin(admin.ModelAdmin):
	list_display = ("student", "class_subject", "term", "total_score", "grade")
	list_filter = ("term", "grade")


@admin.register(TermResult)
class TermResultAdmin(admin.ModelAdmin):
	list_display = ("student", "class_instance", "term", "average_score", "class_position")
	list_filter = ("term",)
