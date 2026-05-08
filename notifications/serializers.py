from rest_framework import serializers
from .models import Notification, SupportTicket, SmsLog

class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['id', 'subject', 'message', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'read', 'created_at']


class SmsLogSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SmsLog
        fields = [
            'id', 'sms_type', 'status',
            'total_recipients', 'sent_count', 'failed_count', 'no_phone_count',
            'message_preview', 'filters_used', 'details',
            'failure_reason', 'sent_by_name', 'created_at',
        ]

    def get_sent_by_name(self, obj):
        if obj.sent_by:
            return obj.sent_by.get_full_name() or obj.sent_by.email
        return None