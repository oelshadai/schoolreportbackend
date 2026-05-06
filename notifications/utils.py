from .models import Notification
from .push_service import send_push_to_user


def create_notification(user, title, message, notification_type='info', url='/'):
    """Helper function to create an in-app notification and fire a Web Push."""
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type,
    )
    # Fire-and-forget push (errors are caught inside)
    try:
        send_push_to_user(user, title, message, url=url)
    except Exception:
        pass
    return notification


def notify_users(users, title, message, notification_type='info', url='/'):
    """Bulk create notifications for multiple users and send Web Push to each."""
    notifications = [
        Notification(user=user, title=title, message=message, type=notification_type)
        for user in users
    ]
    created = Notification.objects.bulk_create(notifications)
    for user in users:
        try:
            send_push_to_user(user, title, message, url=url)
        except Exception:
            pass
    return created