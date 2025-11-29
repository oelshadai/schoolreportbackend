from django.contrib import admin
from .models import ReportCard


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
	list_display = ("student", "term", "status", "report_code", "generated_at", "published_at")
	list_filter = ("status", "term")
	search_fields = ("report_code",)
