"""
Phase 4: Submission API Validation Logic
Complete backend authority for academic submissions
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

from .models_phase4_final import Assignment, StudentAssignment, AcademicViolation
from students.models import Student

logger = logging.getLogger(__name__)


class SubmissionValidationAPI(viewsets.ViewSet):
    """Backend authority for academic submissions with complete validation"""
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
                
                # Validate assignment availability
                now = timezone.now()
                if now < assignment.start_date:
                    return Response({'error': 'Assignment not yet available'}, status=400)
                
                if now > assignment.due_date:
                    return Response({'error': 'Assignment deadline has passed'}, status=400)
                
                # Start attempt (atomic with validation)
                student_assignment = student_assignment.start_attempt()
                
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
        """Submit assignment with comprehensive validation"""
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
                
                # Validate submission eligibility
                if student_assignment.status != 'IN_PROGRESS':
                    return Response({
                        'error': f'Cannot submit: assignment status is {student_assignment.status}'
                    }, status=400)
                
                # Prepare and validate submission data
                submission_data = self._validate_submission_data(request, assignment)
                
                # Submit (atomic)
                student_assignment = student_assignment.submit_assignment(submission_data)
                
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
    
    def _validate_submission_data(self, request, assignment):
        """Validate submission data based on assignment type"""
        submission_data = {}
        
        # Text submission validation
        if request.data.get('submission_text'):
            text = request.data['submission_text'].strip()
            if len(text) > 10000:  # 10KB text limit
                raise ValidationError('Text submission too long (max 10,000 characters)')
            submission_data['text'] = text
        
        # File submission validation
        if 'submission_file' in request.FILES:
            file = request.FILES['submission_file']
            
            # File size validation
            max_size = self._get_max_file_size(assignment.assignment_type)
            if file.size > max_size:
                raise ValidationError(f'File size exceeds {max_size // (1024*1024)}MB limit')
            
            # File type validation
            allowed_extensions = self._get_allowed_extensions(assignment.assignment_type)
            file_ext = file.name.split('.')[-1].lower() if '.' in file.name else ''
            if file_ext not in allowed_extensions:
                raise ValidationError(f'File type .{file_ext} not allowed. Allowed: {", ".join(allowed_extensions)}')
            
            submission_data['file'] = file
        
        # Type-specific validation
        if assignment.assignment_type == 'PROJECT':
            if not submission_data.get('file'):
                raise ValidationError('Projects require file submission')
        
        if assignment.assignment_type in ['HOMEWORK', 'EXERCISE']:
            if not submission_data.get('text') and not submission_data.get('file'):
                raise ValidationError('Text or file submission required')
        
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            if 'answers' not in request.data:
                raise ValidationError('Quiz/Exam requires answers')
            submission_data['answers'] = request.data['answers']
        
        return submission_data
    
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
    
    def _get_allowed_extensions(self, assignment_type):
        """Get allowed file extensions based on assignment type"""
        extensions = {
            'PROJECT': ['pdf', 'doc', 'docx', 'zip', 'rar', 'jpg', 'png', 'txt'],
            'HOMEWORK': ['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'],
            'EXERCISE': ['pdf', 'doc', 'docx', 'jpg', 'png', 'txt'],
            'QUIZ': ['pdf', 'jpg', 'png', 'txt'],
            'EXAM': ['pdf', 'jpg', 'png', 'txt']
        }
        return extensions.get(assignment_type, ['pdf', 'doc', 'docx', 'txt'])
    
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
            student_assignment.refresh_from_db()
            
            return Response({
                'assignment_id': assignment.id,
                'assignment_type': assignment.assignment_type,
                'status': student_assignment.status,
                'attempts_made': student_assignment.attempts_count,
                'max_attempts': assignment.max_attempts,
                'can_start_attempt': self._can_start_attempt(student_assignment),
                'time_remaining': student_assignment.check_time_remaining(),
                'is_locked': student_assignment.is_locked,
                'submitted_at': student_assignment.submitted_at,
                'score': float(student_assignment.score) if student_assignment.score else None,
                'due_date': assignment.due_date,
                'is_overdue': timezone.now() > assignment.due_date,
                'lockdown_violations': student_assignment.lockdown_violations
            })
            
        except StudentAssignment.DoesNotExist:
            now = timezone.now()
            can_start = (now >= assignment.start_date and now <= assignment.due_date)
            
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
                'is_overdue': now > assignment.due_date,
                'lockdown_violations': 0
            })
    
    def _can_start_attempt(self, student_assignment):
        """Check if student can start new attempt"""
        if student_assignment.status in ['SUBMITTED', 'GRADED', 'LOCKED', 'EXPIRED', 'VIOLATED']:
            return False
        
        if student_assignment.attempts_count >= student_assignment.assignment.max_attempts:
            return False
        
        now = timezone.now()
        if now < student_assignment.assignment.start_date or now > student_assignment.assignment.due_date:
            return False
        
        return True
    
    @action(detail=True, methods=['post'], url_path='report-violation')
    def report_violation(self, request, pk=None):
        """Report academic violation with automatic enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            with transaction.atomic():
                student_assignment = StudentAssignment.objects.select_for_update().get(
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
                
                # Auto-fail for serious violations in exams
                if (violation_type in ['LOCKDOWN_BREACH', 'MULTIPLE_TABS'] and 
                    assignment.assignment_type == 'EXAM'):
                    student_assignment.status = 'VIOLATED'
                    student_assignment.is_locked = False
                
                student_assignment.save()
                
                logger.warning(f"Academic violation: Student {student.id}, Assignment {assignment.id}, Type: {violation_type}")
                
                return Response({
                    'violation_id': violation.id,
                    'total_violations': student_assignment.lockdown_violations,
                    'status': student_assignment.status,
                    'message': 'Violation recorded'
                })
                
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            logger.error(f"Error reporting violation: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)