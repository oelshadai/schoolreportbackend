import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Announcement
from .serializers import AnnouncementSerializer

logger = logging.getLogger(__name__)

class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if not user.school:
            return Announcement.objects.none()
        
        queryset = Announcement.objects.filter(school=user.school)
        
        # Filter by audience based on user role
        if user.role == 'STUDENT':
            queryset = queryset.filter(audience__in=['ALL', 'STUDENTS'])
        elif user.role == 'TEACHER':
            queryset = queryset.filter(audience__in=['ALL', 'TEACHERS'])
        elif user.role == 'PARENT':
            queryset = queryset.filter(audience__in=['ALL', 'PARENTS'])

        return queryset.order_by('-is_pinned', '-created_at')
    
    def create(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role not in ['SCHOOL_ADMIN', 'SUPER_ADMIN', 'PRINCIPAL']:
            return Response(
                {'error': 'Only administrators can create announcements'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        send_sms = request.data.get('send_sms_to_parents', False)
        response = super().create(request, *args, **kwargs)

        if send_sms and response.status_code == 201:
            try:
                from notifications.sms_service import SmsService
                from students.models import Student
                school = request.user.school
                if getattr(school, 'sms_enabled', False):
                    students_qs = Student.objects.filter(
                        school=school, is_active=True
                    ).exclude(guardian_phone='')
                    phones = list({s.guardian_phone for s in students_qs if s.guardian_phone})
                    if phones:
                        title = request.data.get('title', 'Announcement')
                        content = request.data.get('content', '')
                        message = f'[{school.name}] {title}: {content}'
                        if len(message) > 160:
                            message = message[:157] + '...'
                        sent = SmsService.send(phones, message, school)
                        sms_sent_count = len(phones) if sent else 0
                        response.data['sms_sent'] = sms_sent_count
                        # Log the announcement SMS dispatch
                        try:
                            from notifications.models import SmsLog
                            SmsLog.objects.create(
                                school=school,
                                sent_by=request.user,
                                sms_type='general',
                                status='success' if sent else 'failed',
                                total_recipients=len(phones),
                                sent_count=sms_sent_count,
                                failed_count=0 if sent else len(phones),
                                no_phone_count=0,
                                message_preview=message[:160],
                                filters_used={'announcement_title': request.data.get('title', '')},
                                details=[],
                            )
                        except Exception as log_err:
                            logger.warning(f'SmsLog creation failed for announcement: {log_err}')
                    else:
                        response.data['sms_sent'] = 0
                else:
                    response.data['sms_sent'] = 0
                    response.data['sms_note'] = 'SMS is not enabled for this school'
            except Exception as e:
                logger.error(f'Announcement SMS error: {e}')
                response.data['sms_sent'] = 0

        return response
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, created_by=self.request.user)
    
    def update(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role not in ['SCHOOL_ADMIN', 'SUPER_ADMIN', 'PRINCIPAL']:
            return Response(
                {'error': 'Only administrators can update announcements'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role not in ['SCHOOL_ADMIN', 'SUPER_ADMIN', 'PRINCIPAL']:
            return Response(
                {'error': 'Only administrators can delete announcements'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)