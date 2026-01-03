from django.db import models
from django.contrib.auth.models import User
from schools.models import Class

class VirtualSession(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live'),
        ('ENDED', 'Ended'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virtual_sessions')
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='virtual_sessions')
    scheduled_time = models.DateTimeField()
    duration = models.IntegerField(default=60)  # minutes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    meeting_url = models.URLField(blank=True, null=True)
    recording_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scheduled_time']

class SessionParticipant(models.Model):
    session = models.ForeignKey(VirtualSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_present = models.BooleanField(default=True)

class SessionMessage(models.Model):
    session = models.ForeignKey(VirtualSession, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

class Quiz(models.Model):
    session = models.ForeignKey(VirtualSession, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    question = models.TextField()
    options = models.JSONField()  # Store as JSON array
    correct_answer = models.IntegerField()  # Index of correct option
    time_limit = models.IntegerField(default=30)  # seconds
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class QuizResponse(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_option = models.IntegerField()
    is_correct = models.BooleanField()
    response_time = models.FloatField()  # seconds taken to respond
    timestamp = models.DateTimeField(auto_now_add=True)