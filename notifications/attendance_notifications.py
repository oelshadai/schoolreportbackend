from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def notify_admins_attendance_taken(school, teacher, class_obj, date):
    """Notify school admins when a teacher takes attendance"""
    try:
        # Get all school admins and principals
        admins = User.objects.filter(
            school=school,
            role__in=['SCHOOL_ADMIN', 'PRINCIPAL']
        )
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="📋 Attendance Taken",
                message=f"{teacher.get_full_name()} has taken attendance for {class_obj.name} on {date}",
                type='info'
            )
            
    except Exception as e:
        print(f"Failed to notify admins about attendance: {e}")