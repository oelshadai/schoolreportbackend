from django.db import models
from django.conf import settings
from schools.models import Class, ClassSubject


class LessonSlot(models.Model):
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
    ]

    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lesson_slots')
    class_subject  = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='lesson_slots')
    day            = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time     = models.TimeField()
    end_time       = models.TimeField()
    room           = models.CharField(max_length=100, blank=True, default='')
    notes          = models.CharField(max_length=255, blank=True, default='')
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lesson_slots'
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.class_instance} | {self.get_day_display()} {self.start_time:%H:%M} — {self.class_subject.subject.name}"
