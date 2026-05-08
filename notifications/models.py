from django.db import models
from django.conf import settings


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PushSub({self.user_id}) {self.endpoint[:60]}"

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.user.get_full_name()}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('attendance', 'Attendance'),
        ('assignment', 'Assignment'),
        ('fee', 'Fee'),
        ('general', 'General'),
        ('warning', 'Warning'),
        ('success', 'Success'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    activity_type = models.CharField(max_length=50, blank=True)  # 'attendance_taken', 'assignment_created', 'fee_set'
    class_name = models.CharField(max_length=100, blank=True)
    teacher_name = models.CharField(max_length=100, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional references
    class_id = models.IntegerField(null=True, blank=True)
    assignment_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"


class SmsLog(models.Model):
    """
    Audit log for every SMS batch dispatch.
    Created once per send_fee_reminders call (or any bulk SMS action).
    """
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    TYPE_CHOICES = [
        ('fee_reminder', 'Fee Reminder'),
        ('attendance', 'Attendance Alert'),
        ('general', 'General'),
    ]

    school = models.ForeignKey(
        'schools.School', on_delete=models.CASCADE, related_name='sms_logs'
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sms_logs_sent'
    )
    sms_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Counts
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    no_phone_count = models.IntegerField(default=0)

    # Message & filters used
    message_preview = models.TextField(blank=True)  # first 200 chars of message
    filters_used = models.JSONField(default=dict, blank=True)  # {class, fee_type, statuses}

    # Per-recipient detail snapshot
    details = models.JSONField(default=list, blank=True)

    failure_reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'sms_logs'

    def __str__(self):
        return f"SmsLog[{self.sms_type}] {self.school_id} — {self.sent_count}/{self.total_recipients} sent @ {self.created_at:%Y-%m-%d %H:%M}"