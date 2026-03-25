from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Announcement
from .serializers import AnnouncementSerializer

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
        
        return queryset.order_by('-is_pinned', '-created_at')
    
    def create(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role not in ['SCHOOL_ADMIN', 'SUPER_ADMIN', 'PRINCIPAL']:
            return Response(
                {'error': 'Only administrators can create announcements'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
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