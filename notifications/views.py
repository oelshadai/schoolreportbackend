from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import Notification, SupportTicket
from .serializers import NotificationSerializer, SupportTicketSerializer
from django.db.models import Q
from .email_service import EmailService
from django.conf import settings

User = get_user_model()

class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        ticket = serializer.save(user=self.request.user)
        # Send email to superadmin
        try:
            superadmins = User.objects.filter(role='SUPERADMIN')
            for superadmin in superadmins:
                EmailService.send_support_ticket_notification(superadmin, ticket)
        except Exception as e:
            pass  # Continue even if email fails
        return ticket

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'SCHOOL_ADMIN':
            return Notification.objects.filter(
                Q(user=user) | Q(user__school=user.school)
            ).distinct()
        else:
            return Notification.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(read=False).count()
        return Response({'count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True)
        return Response({'updated': updated})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'marked as read'})


def create_notification(user, title, message, notification_type='general', 
                       activity_type='', class_name='', teacher_name='', 
                       class_id=None, assignment_id=None):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type,
        activity_type=activity_type,
        class_name=class_name,
        teacher_name=teacher_name,
        class_id=class_id,
        assignment_id=assignment_id
    )


def notify_admins_attendance_taken(school, teacher, class_obj, date):
    admins = User.objects.filter(school=school, role='SCHOOL_ADMIN')
    for admin in admins:
        create_notification(
            user=admin,
            title=f"Attendance Taken - {class_obj.name}",
            message=f"{teacher.get_full_name()} took attendance for {class_obj.name} on {date.strftime('%B %d, %Y')}",
            notification_type='attendance',
            activity_type='attendance_taken',
            class_name=class_obj.name,
            teacher_name=teacher.get_full_name(),
            class_id=class_obj.id
        )


def notify_admins_assignment_created(school, teacher, assignment, class_obj):
    admins = User.objects.filter(school=school, role='SCHOOL_ADMIN')
    for admin in admins:
        create_notification(
            user=admin,
            title=f"New Assignment - {assignment.title}",
            message=f"{teacher.get_full_name()} created '{assignment.title}' for {class_obj.name}",
            notification_type='assignment',
            activity_type='assignment_created',
            class_name=class_obj.name,
            teacher_name=teacher.get_full_name(),
            class_id=class_obj.id,
            assignment_id=assignment.id
        )


def notify_admins_fee_set(school, admin_user, fee_type, amount, class_obj=None):
    admins = User.objects.filter(school=school, role='SCHOOL_ADMIN').exclude(id=admin_user.id)
    class_info = f" for {class_obj.name}" if class_obj else ""
    for admin in admins:
        create_notification(
            user=admin,
            title=f"Fee Set - {fee_type}",
            message=f"{admin_user.get_full_name()} set {fee_type} fee to ${amount}{class_info}",
            notification_type='fee',
            activity_type='fee_set',
            class_name=class_obj.name if class_obj else '',
            teacher_name=admin_user.get_full_name(),
            class_id=class_obj.id if class_obj else None
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def announcements_list(request):
    """Get announcements for students"""
    try:
        notifications = Notification.objects.filter(
            user=request.user,
            type__in=['announcement', 'info', 'warning']
        ).order_by('-created_at')[:10]
        
        announcements = [{
            'id': notif.id,
            'title': notif.title,
            'content': notif.message,
            'created_at': notif.created_at.isoformat(),
            'priority': 'high' if notif.type == 'error' else 'medium',
            'read': notif.read
        } for notif in notifications]
        
        return Response(announcements)
    except Exception as e:
        return Response([], status=200)  # Return empty list instead of error