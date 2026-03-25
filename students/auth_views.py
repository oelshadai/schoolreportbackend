from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from .models import Student
from .serializers import StudentAssignmentSerializer
from assignments.models import StudentAssignment, Assignment
import logging
import hashlib
import time

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def student_login(request):
    """Production-safe student login endpoint"""
    try:
        student_id = request.data.get('student_id')
        password = request.data.get('password')

        if not student_id or not password:
            return Response(
                {'error': 'Student ID and password required'},
                status=400
            )

        student_id = str(student_id).strip()

        try:
            student = Student.objects.select_related('user').get(student_id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        if not student.user:
            return Response({'error': 'Student account misconfigured'}, status=500)

        if not student.user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=401)

        try:
            refresh = RefreshToken.for_user(student.user)
        except Exception as e:
            logger.error(f"Token generation error: {str(e)}")
            return Response({'error': 'Token generation failed'}, status=500)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': student.user.id,
                'email': student.user.email,
                'first_name': student.user.first_name or '',
                'last_name': student.user.last_name or '',
                'role': 'STUDENT'
            }
        }, status=200)

    except Exception as e:
        logger.exception(f"Login error: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def student_refresh_token(request):
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'error': 'Refresh token required'}, status=400)
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            return Response({
                'access': access_token,
                'refresh': str(refresh)
            })
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return Response({'error': 'Invalid or expired refresh token'}, status=401)
            
    except Exception as e:
        logger.exception(f"Unexpected error in token refresh: {str(e)}")
        return Response({'error': 'Token refresh failed'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    """Get student dashboard with real data from database"""
    try:
        student = Student.objects.select_related('user', 'current_class', 'school').get(user=request.user)
    except Student.DoesNotExist:
        return Response({'detail': 'Student profile not found'}, status=404)

    try:
        # Get student assignments
        assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        ).select_related('assignment', 'assignment__class_subject__subject')

        # Get classmates
        classmates = []
        if student.current_class:
            classmates_qs = Student.objects.filter(
                current_class=student.current_class
            ).exclude(id=student.id).select_related('user')[:10]
            classmates = [{
                'id': c.id,
                'name': c.get_full_name(),
                'student_id': c.student_id,
                'email': c.user.email if c.user else None,
            } for c in classmates_qs]

        # Calculate stats
        total_assignments = assignments.count()
        completed = assignments.filter(status='SUBMITTED').count()
        graded = assignments.filter(status='GRADED').count()
        pending = assignments.filter(status__in=['NOT_STARTED', 'IN_PROGRESS']).count()

        response_data = {
            'student': {
                'id': student.id,
                'name': student.get_full_name(),
                'first_name': student.first_name,
                'last_name': student.last_name,
                'other_names': student.other_names or '',
                'student_id': student.student_id,
                'email': student.user.email if student.user else None,
                'class': student.current_class.level if student.current_class else 'No Class',
                'class_id': student.current_class.id if student.current_class else None,
                'gender': student.gender,
                'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
                'school': student.school.name if student.school else None,
                'school_id': student.school.id if student.school else None,
                'photo': student.photo.url if student.photo else None,
                'guardian_name': student.guardian_name,
                'guardian_phone': student.guardian_phone,
                'guardian_email': student.guardian_email,
                'admission_date': student.admission_date.isoformat() if student.admission_date else None,
                'is_active': student.is_active,
                'role': 'STUDENT'
            },
            'assignments': StudentAssignmentSerializer(assignments, many=True).data,
            'classmates': classmates,
            'stats': {
                'total_assignments': total_assignments,
                'completed': completed,
                'pending': pending,
                'graded': graded
            }
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        try:
            return Response({
                'student': {
                    'id': student.id,
                    'name': student.get_full_name(),
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'other_names': student.other_names or '',
                    'student_id': student.student_id,
                    'email': student.user.email if student.user else None,
                    'class': student.current_class.level if student.current_class else 'No Class',
                    'class_id': student.current_class.id if student.current_class else None,
                    'gender': student.gender,
                    'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
                    'school': student.school.name if student.school else None,
                    'school_id': student.school.id if student.school else None,
                    'photo': student.photo.url if student.photo else None,
                    'guardian_name': student.guardian_name,
                    'guardian_phone': student.guardian_phone,
                    'guardian_email': student.guardian_email,
                    'admission_date': student.admission_date.isoformat() if student.admission_date else None,
                    'is_active': student.is_active,
                    'role': 'STUDENT'
                },
                'assignments': [],
                'classmates': [],
                'stats': {
                    'total_assignments': 0,
                    'completed': 0,
                    'pending': 0,
                    'graded': 0
                }
            })
        except Exception:
            return Response({'error': 'Dashboard error'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_logout(request):
    """Secure student logout"""
    try:
        refresh_token = request.data.get('refresh')
        access_token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        
        if access_token:
            token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            cache.set(f"blacklisted_token:{token_hash}", True, 86400)
        
        if hasattr(request.user, 'student_profile'):
            student = request.user.student_profile
            cache.delete(f"student_session:{student.student_id}")
        
        return Response(
            {'detail': 'Successfully logged out'},
            status=200
        )
        
    except Exception:
        return Response(
            {'detail': 'Logout completed'},
            status=200
        )