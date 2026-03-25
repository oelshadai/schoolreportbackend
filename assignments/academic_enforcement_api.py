"""
Phase 4: Academic Submission API with Atomic Enforcement
All academic rules enforced server-side with atomic transactions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
import logging

from .models_phase4 import Assignment, StudentAssignment, AcademicViolation
from students.models import Student

logger = logging.getLogger(__name__)


class AcademicEnforcementAPI(viewsets.ViewSet):
    """Backend authority for academic submissions"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'], url_path='start-attempt')
    def start_attempt(self, request, pk=None):
        """Start assignment attempt with atomic enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            with transaction.atomic():
                # Get or create student assignment
                student_assignment, created = StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
                
                # Start attempt (atomic with validation)
                student_assignment = student_assignment.start_attempt()
                
                # Log attempt start
                logger.info(f"Student {student.id} started attempt {student_assignment.attempts_count} for assignment {assignment.id}")
                
                return Response({
                    'assignment_id': assignment.id,
                    'attempt_number': student_assignment.attempts_count,
                    'max_attempts': assignment.max_attempts,
                    'time_limit_minutes': assignment.time_limit_minutes,
                    'started_at': student_assignment.current_attempt_started_at,
                    'assignment_type': assignment.assignment_type,
                    'requires_lockdown': assignment.requires_lockdown,
                    'is_locked': student_assignment.is_locked,
                    'time_remaining': student_assignment.check_time_remaining()
                })
                
        except ValidationError as e:
            logger.warning(f"Attempt start failed for student {student.id}, assignment {assignment.id}: {str(e)}")
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error starting attempt: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)
    
    @action(detail=True, methods=['post'], url_path='submit')
    def submit_assignment(self, request, pk=None):
        """Submit assignment with atomic validation"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            with transaction.atomic():
                student_assignment = StudentAssignment.objects.select_for_update().get(
                    assignment=assignment,
                    student=student
                )
                
                # Auto-expire check
                if student_assignment.auto_expire_if_needed():
                    return Response({
                        'error': 'Assignment auto-expired due to time limit',
                        'status': 'EXPIRED'
                    }, status=400)
                
                # Prepare submission data
                submission_data = {}
                
                # Text submission
                if request.data.get('submission_text'):
                    submission_data['text'] = request.data['submission_text'].strip()
                
                # File submission
                if 'submission_file' in request.FILES:
                    file = request.FILES['submission_file']
                    
                    # File validation
                    max_size = self._get_max_file_size(assignment.assignment_type)
                    if file.size > max_size:
                        return Response({
                            'error': f'File size exceeds {max_size // (1024*1024)}MB limit'
                        }, status=400)
                    
                    submission_data['file'] = file
                
                # Type-specific validation
                if assignment.assignment_type == 'PROJECT' and not submission_data.get('file'):
                    return Response({'error': 'Projects require file submission'}, status=400)
                
                if assignment.assignment_type in ['HOMEWORK', 'EXERCISE'] and not submission_data.get('text'):
                    return Response({'error': 'Text submission required'}, status=400)
                
                # Submit (atomic)
                student_assignment = student_assignment.submit_assignment(submission_data)
                
                # Log submission
                logger.info(f"Student {student.id} submitted assignment {assignment.id}, attempt {student_assignment.attempts_count}")
                
                return Response({
                    'message': 'Assignment submitted successfully',
                    'submitted_at': student_assignment.submitted_at,
                    'attempt_number': student_assignment.attempts_count,
                    'status': student_assignment.status,
                    'can_retry': student_assignment.attempts_count < assignment.max_attempts
                })
                
        except ValidationError as e:
            logger.warning(f"Submission failed for student {student.id}, assignment {assignment.id}: {str(e)}")
            return Response({'error': str(e)}, status=400)
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not started'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during submission: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)
    
    @action(detail=True, methods=['get'], url_path='status')
    def get_assignment_status(self, request, pk=None):
        """Get assignment status with time enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
            
            # Auto-expire check
            student_assignment.auto_expire_if_needed()
            
            # Refresh from database
            student_assignment.refresh_from_db()
            
            return Response({
                'assignment_id': assignment.id,
                'assignment_type': assignment.assignment_type,
                'status': student_assignment.status,
                'attempts_made': student_assignment.attempts_count,
                'max_attempts': assignment.max_attempts,
                'can_start_attempt': student_assignment.status == 'NOT_STARTED' and student_assignment.attempts_count < assignment.max_attempts,
                'time_remaining': student_assignment.check_time_remaining(),
                'is_locked': student_assignment.is_locked,
                'submitted_at': student_assignment.submitted_at,
                'score': float(student_assignment.score) if student_assignment.score else None,
                'due_date': assignment.due_date,
                'is_overdue': timezone.now() > assignment.due_date
            })
            
        except StudentAssignment.DoesNotExist:
            # Check if assignment is still available
            now = timezone.now()
            can_start = (now >= assignment.start_date and 
                        now <= assignment.due_date)
            
            return Response({
                'assignment_id': assignment.id,
                'assignment_type': assignment.assignment_type,
                'status': 'NOT_STARTED',
                'attempts_made': 0,
                'max_attempts': assignment.max_attempts,
                'can_start_attempt': can_start,
                'time_remaining': None,
                'is_locked': False,
                'submitted_at': None,
                'score': None,
                'due_date': assignment.due_date,
                'is_overdue': now > assignment.due_date
            })
    
    @action(detail=True, methods=['post'], url_path='report-violation')
    def report_violation(self, request, pk=None):
        """Report academic violation"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
            
            violation_type = request.data.get('violation_type')
            description = request.data.get('description', '')
            
            if violation_type not in dict(AcademicViolation.VIOLATION_TYPES):
                return Response({'error': 'Invalid violation type'}, status=400)
            
            # Create violation record
            violation = AcademicViolation.objects.create(
                student_assignment=student_assignment,
                violation_type=violation_type,
                description=description
            )
            
            # Update violation count
            student_assignment.lockdown_violations += 1
            
            # Auto-fail for serious violations
            if violation_type in ['LOCKDOWN_BREACH', 'MULTIPLE_TABS'] and assignment.assignment_type == 'EXAM':
                student_assignment.status = 'VIOLATED'
                student_assignment.is_locked = False
            
            student_assignment.save()
            
            logger.warning(f"Academic violation reported: Student {student.id}, Assignment {assignment.id}, Type: {violation_type}")
            
            return Response({
                'violation_id': violation.id,
                'total_violations': student_assignment.lockdown_violations,
                'status': student_assignment.status
            })
            
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
    
    def _get_max_file_size(self, assignment_type):
        """Get max file size based on assignment type"""
        sizes = {
            'PROJECT': 50 * 1024 * 1024,  # 50MB
            'HOMEWORK': 10 * 1024 * 1024,  # 10MB
            'EXERCISE': 5 * 1024 * 1024,   # 5MB
            'QUIZ': 2 * 1024 * 1024,       # 2MB
            'EXAM': 2 * 1024 * 1024,       # 2MB
        }
        return sizes.get(assignment_type, 10 * 1024 * 1024)