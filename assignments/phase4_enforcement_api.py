"""
Phase 4: Academic Enforcement API Endpoints
Minimal implementation for academic enforcement management
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import logging

from .models_phase4_final import Assignment, StudentAssignment, AcademicViolation
from students.models import Student

logger = logging.getLogger(__name__)


class EnforcementAPI(viewsets.ViewSet):
    """Academic enforcement management API"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='violations')
    def get_violations(self, request):
        """Get academic violations for current user"""
        try:
            student = get_object_or_404(Student, user=request.user)
            violations = AcademicViolation.objects.filter(
                student_assignment__student=student
            ).order_by('-created_at')[:10]
            
            return Response([{
                'id': v.id,
                'type': v.violation_type,
                'description': v.description,
                'created_at': v.created_at,
                'assignment_title': v.student_assignment.assignment.title
            } for v in violations])
            
        except Exception as e:
            logger.error(f"Error fetching violations: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)
    
    @action(detail=True, methods=['post'], url_path='lock')
    def lock_assignment(self, request, pk=None):
        """Lock assignment for violations"""
        try:
            assignment = get_object_or_404(Assignment, id=pk)
            student = get_object_or_404(Student, user=request.user)
            
            with transaction.atomic():
                student_assignment = StudentAssignment.objects.select_for_update().get(
                    assignment=assignment,
                    student=student
                )
                
                student_assignment.is_locked = True
                student_assignment.status = 'LOCKED'
                student_assignment.save()
                
                return Response({'message': 'Assignment locked'})
                
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            logger.error(f"Error locking assignment: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)