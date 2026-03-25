from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models_phase4_enforcement import EnforcementManager, StudentSubmissionAttempt, AcademicViolation
from .models import Assignment
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_assignment_attempt(request, assignment_id):
    """Start new assignment attempt with enforcement validation"""
    try:
        student = request.user.student_profile
        
        with transaction.atomic():
            # Validate and create attempt
            attempt, message = EnforcementManager.create_submission_attempt(
                student.id, assignment_id
            )
            
            if not attempt:
                return Response({
                    'success': False,
                    'error': message,
                    'code': 'VALIDATION_FAILED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get assignment details for frontend
            assignment = Assignment.objects.select_related('enforcement').get(id=assignment_id)
            
            return Response({
                'success': True,
                'attempt_id': str(attempt.id),
                'attempt_number': attempt.attempt_number,
                'time_limit_minutes': assignment.enforcement.time_limit_minutes,
                'max_attempts': assignment.enforcement.max_attempts,
                'remaining_attempts': assignment.enforcement.max_attempts - attempt.attempt_number,
                'started_at': attempt.started_at.isoformat()
            })
            
    except Exception as e:
        logger.error(f"Assignment attempt start error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_assignment_attempt(request, attempt_id):
    """Submit assignment attempt with enforcement validation"""
    try:
        submission_data = request.data.get('submission', {})
        
        with transaction.atomic():
            # Validate attempt ownership
            attempt = StudentSubmissionAttempt.objects.select_for_update().get(
                id=attempt_id,
                student=request.user.student_profile
            )
            
            if attempt.submitted_at:
                return Response({
                    'success': False,
                    'error': 'Attempt already submitted',
                    'code': 'ALREADY_SUBMITTED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Finalize submission with enforcement
            success, message = EnforcementManager.finalize_submission(
                attempt_id, submission_data
            )
            
            if not success:
                return Response({
                    'success': False,
                    'error': message,
                    'code': 'SUBMISSION_FAILED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Refresh attempt data
            attempt.refresh_from_db()
            
            return Response({
                'success': True,
                'submitted_at': attempt.submitted_at.isoformat(),
                'time_spent_seconds': attempt.time_spent_seconds,
                'is_valid': attempt.is_valid,
                'violation_reason': attempt.violation_reason or None
            })
            
    except StudentSubmissionAttempt.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid attempt ID',
            'code': 'INVALID_ATTEMPT'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Assignment submission error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignment_enforcement_status(request, assignment_id):
    """Get enforcement status for assignment"""
    try:
        student = request.user.student_profile
        assignment = Assignment.objects.select_related('enforcement').get(id=assignment_id)
        
        # Get attempt history
        attempts = StudentSubmissionAttempt.objects.filter(
            student=student,
            assignment_id=assignment_id
        ).order_by('attempt_number')
        
        # Get violations
        violations = AcademicViolation.objects.filter(
            student=student,
            assignment_id=assignment_id
        ).order_by('-detected_at')
        
        # Check if can attempt
        can_attempt = True
        reason = None
        
        if attempts.count() >= assignment.enforcement.max_attempts:
            can_attempt = False
            reason = "Maximum attempts reached"
        elif timezone.now() > assignment.enforcement.submission_deadline:
            can_attempt = False
            reason = "Submission deadline passed"
        
        return Response({
            'assignment_id': assignment_id,
            'enforcement': {
                'max_attempts': assignment.enforcement.max_attempts,
                'time_limit_minutes': assignment.enforcement.time_limit_minutes,
                'submission_deadline': assignment.enforcement.submission_deadline.isoformat(),
                'late_submission_penalty': float(assignment.enforcement.late_submission_penalty),
                'auto_submit_on_timeout': assignment.enforcement.auto_submit_on_timeout
            },
            'student_status': {
                'attempts_made': attempts.count(),
                'remaining_attempts': max(0, assignment.enforcement.max_attempts - attempts.count()),
                'can_attempt': can_attempt,
                'restriction_reason': reason,
                'has_violations': violations.exists()
            },
            'attempts': [{
                'attempt_number': attempt.attempt_number,
                'started_at': attempt.started_at.isoformat(),
                'submitted_at': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                'time_spent_seconds': attempt.time_spent_seconds,
                'is_valid': attempt.is_valid,
                'violation_reason': attempt.violation_reason
            } for attempt in attempts],
            'violations': [{
                'violation_type': violation.violation_type,
                'severity': violation.severity,
                'detected_at': violation.detected_at.isoformat(),
                'is_resolved': violation.is_resolved
            } for violation in violations[:5]]  # Limit to recent violations
        })
        
    except Assignment.DoesNotExist:
        return Response({
            'error': 'Assignment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Enforcement status error: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_submission_eligibility(request, assignment_id):
    """Pre-validate if student can submit assignment"""
    try:
        student = request.user.student_profile
        
        is_valid, message = EnforcementManager.validate_submission_attempt(
            student.id, assignment_id
        )
        
        return Response({
            'eligible': is_valid,
            'message': message,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Eligibility validation error: {str(e)}")
        return Response({
            'eligible': False,
            'message': 'Validation error occurred',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_attempt(request, assignment_id):
    """Get currently active attempt for assignment"""
    try:
        student = request.user.student_profile
        
        active_attempt = StudentSubmissionAttempt.objects.filter(
            student=student,
            assignment_id=assignment_id,
            submitted_at__isnull=True
        ).first()
        
        if not active_attempt:
            return Response({
                'has_active_attempt': False
            })
        
        # Calculate remaining time
        assignment = Assignment.objects.select_related('enforcement').get(id=assignment_id)
        remaining_seconds = None
        
        if assignment.enforcement.time_limit_minutes:
            elapsed_seconds = (timezone.now() - active_attempt.started_at).total_seconds()
            total_seconds = assignment.enforcement.time_limit_minutes * 60
            remaining_seconds = max(0, total_seconds - elapsed_seconds)
        
        return Response({
            'has_active_attempt': True,
            'attempt_id': str(active_attempt.id),
            'attempt_number': active_attempt.attempt_number,
            'started_at': active_attempt.started_at.isoformat(),
            'elapsed_seconds': int((timezone.now() - active_attempt.started_at).total_seconds()),
            'remaining_seconds': int(remaining_seconds) if remaining_seconds is not None else None,
            'time_limit_minutes': assignment.enforcement.time_limit_minutes
        })
        
    except Assignment.DoesNotExist:
        return Response({
            'error': 'Assignment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Active attempt check error: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)