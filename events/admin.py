from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'time', 'type', 'status', 'school']
    list_filter = ['type', 'status', 'date', 'school']
    search_fields = ['title', 'description']
    ordering = ['date', 'time']