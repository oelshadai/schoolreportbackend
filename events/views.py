from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from .models import Event
from .serializers import EventSerializer

class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Event.objects.filter(school=self.request.user.school)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        stats = {
            'total_events': queryset.count(),
            'this_month': queryset.filter(date__month=request.GET.get('month', 3)).count(),
            'confirmed': queryset.filter(status='confirmed').count(),
            'total_attendees': sum(event.attendees for event in queryset)
        }
        return Response(stats)