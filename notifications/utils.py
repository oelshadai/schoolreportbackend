from .models import Notification

def create_notification(user, title, message, notification_type='info'):
    """Helper function to create notifications"""
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type
    )

def notify_users(users, title, message, notification_type='info'):
    """Bulk create notifications for multiple users"""
    notifications = [
        Notification(user=user, title=title, message=message, type=notification_type)
        for user in users
    ]
    return Notification.objects.bulk_create(notifications)