"""
Academic Time Enforcement Middleware
Automatically handles time limit expiration
"""
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import StudentAssignment


class AcademicTimeEnforcementMiddleware(MiddlewareMixin):
    """Middleware to enforce time limits on assignments"""
    
    def process_request(self, request):
        """Check for expired assignments on each request"""
        if request.user.is_authenticated and hasattr(request.user, 'student'):
            # Find all in-progress timed assignments
            expired_assignments = StudentAssignment.objects.filter(
                student=request.user.student,
                status='IN_PROGRESS',
                assignment__is_timed=True,
                current_attempt_started_at__isnull=False
            )
            
            for student_assignment in expired_assignments:
                # Check if time limit exceeded
                if student_assignment.check_time_limit():
                    student_assignment.auto_submit_if_expired()
        
        return None


class ExamLockingMiddleware(MiddlewareMixin):
    """Prevent navigation during locked exams"""
    
    def process_request(self, request):
        """Block non-exam requests during locked exam"""
        if (request.user.is_authenticated and 
            hasattr(request.user, 'student') and
            not request.path.startswith('/api/assignments/')):
            
            # Check if student has locked exam
            locked_exam = StudentAssignment.objects.filter(
                student=request.user.student,
                status='IN_PROGRESS',
                is_locked=True,
                assignment__assignment_type='EXAM'
            ).first()
            
            if locked_exam:
                # Allow only exam-related endpoints
                allowed_paths = [
                    f'/api/assignments/{locked_exam.assignment.id}/',
                    '/api/assignments/submit-quiz/',
                    '/api/assignments/status/',
                    '/logout/'
                ]
                
                if not any(request.path.startswith(path) for path in allowed_paths):
                    from django.http import JsonResponse
                    return JsonResponse({
                        'error': 'Exam in progress - navigation blocked',
                        'exam_id': locked_exam.assignment.id
                    }, status=423)  # Locked
        
        return None