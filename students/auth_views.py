from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Student
from assignments.models import Assignment, StudentAssignment
from assignments.serializers import StudentAssignmentSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def student_login(request):
    """Student login endpoint"""
    student_id = request.data.get('student_id') or request.data.get('username')
    password = request.data.get('password')
    
    print(f"Login attempt - Student ID: {student_id}, Password provided: {bool(password)}")
    
    if not student_id or not password:
        return Response({'detail': 'Student ID and password are required'}, status=400)
    
    try:
        # Find student by student_id
        student = Student.objects.get(student_id=student_id)
        print(f"Found student: {student.get_full_name()}")
        
        # Check if student has a user account
        if not student.user:
            print("Student has no user account")
            return Response({'detail': 'Student account not properly configured. Please contact your school administrator.'}, status=404)
        
        # Simple password check - use the student's password field directly
        if hasattr(student, 'password') and student.password == password:
            user = student.user
            print("Password matched using student.password")
        else:
            print("Password did not match")
            return Response({'detail': 'Invalid credentials'}, status=401)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Get student assignments
        assignments = StudentAssignment.objects.filter(student=student).select_related('assignment')
        print(f"Found {assignments.count()} assignments for student")
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'student': {
                'id': student.id,
                'name': student.get_full_name(),
                'student_id': student.student_id,
                'class': student.current_class.level if student.current_class else 'No Class',
                'username': getattr(student, 'username', student.student_id),
                'role': 'STUDENT'
            },
            'assignments': StudentAssignmentSerializer(assignments, many=True).data,
            'virtual_sessions': [],
            'reports': [],
            'materials': [],
            'stats': {
                'total_assignments': assignments.count(),
                'completed': assignments.filter(status='SUBMITTED').count(),
                'pending': assignments.filter(status='ASSIGNED').count(),
                'graded': assignments.filter(status='GRADED').count()
            }
        })
        
    except Student.DoesNotExist:
        print(f"Student not found: {student_id}")
        return Response({'detail': f'Student not found: {student_id}'}, status=404)
    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response({'detail': f'Login failed: {str(e)}'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    """Get student dashboard data"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'detail': 'Student profile not found'}, status=404)
    
    # Get all published assignments for the student's class
    published_assignments = Assignment.objects.filter(
        class_instance=student.current_class,
        status='PUBLISHED'
    ) if student.current_class else Assignment.objects.none()
    
    print(f"Found {published_assignments.count()} published assignments for class {student.current_class}")
    
    # Create missing StudentAssignment records for published assignments
    created_count = 0
    for assignment in published_assignments:
        student_assignment, created = StudentAssignment.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'status': 'NOT_STARTED'}
        )
        if created:
            created_count += 1
            print(f"Created StudentAssignment for: {assignment.title}")
    
    if created_count > 0:
        print(f"Created {created_count} new student assignments")
    
    # Get all student assignments for published assignments
    assignments = StudentAssignment.objects.filter(
        student=student,
        assignment__status='PUBLISHED'
    ).select_related('assignment')
    
    print(f"Student {student.get_full_name()} has {assignments.count()} assignments")
    
    # Debug: Print assignment details
    for sa in assignments:
        print(f"  - {sa.assignment.title} (Status: {sa.status}, Assignment Status: {sa.assignment.status})")
    
    # Get classmates (students in the same class)
    classmates = []
    if student.current_class:
        classmates_qs = Student.objects.filter(
            current_class=student.current_class
        ).exclude(id=student.id).select_related('user')
        
        classmates = [{
            'id': classmate.id,
            'name': classmate.get_full_name(),
            'avatar': None,
            'status': 'offline',  # TODO: Implement real online status
            'last_seen': classmate.user.last_login if classmate.user else None
        } for classmate in classmates_qs]
    
    # Get announcements (from notifications)
    try:
        from notifications.models import Notification
        notifications_qs = Notification.objects.filter(
            user=request.user,
            read=False
        ).order_by('-created_at')[:10]
        
        announcements = [{
            'id': notif.id,
            'title': notif.title,
            'content': notif.message,
            'date': notif.created_at.isoformat(),
            'priority': 'high' if notif.type == 'error' else 'medium'
        } for notif in notifications_qs]
    except:
        announcements = []
    
    # Get student reports
    try:
        from reports.models import ReportCard
        reports_qs = ReportCard.objects.filter(
            student=student,
            status__in=['GENERATED', 'PUBLISHED']
        ).order_by('-created_at')[:10]
        
        reports = [{
            'id': report.id,
            'title': f'{report.term} Report Card',
            'term': str(report.term),
            'date': report.created_at.isoformat(),
            'type': 'academic',
            'status': 'available'
        } for report in reports_qs]
    except:
        reports = []
    
    # Get virtual classroom sessions for student's class
    try:
        from schools.models import VirtualSession
        sessions = VirtualSession.objects.filter(
            class_assigned=student.current_class,
            status__in=['SCHEDULED', 'LIVE']
        ) if student.current_class else []
    except:
        sessions = []
    
    response_data = {
        'student': {
            'id': student.id,
            'name': student.get_full_name(),
            'student_id': student.student_id,
            'class': student.current_class.level if student.current_class else 'No Class'
        },
        'assignments': StudentAssignmentSerializer(assignments, many=True).data,
        'classmates': classmates,
        'announcements': announcements,
        'reports': reports,
        'virtual_sessions': [
            {
                'id': session.id,
                'title': session.title,
                'scheduled_time': session.scheduled_time,
                'status': session.status,
                'duration': session.duration
            } for session in sessions
        ],
        'stats': {
            'total_assignments': assignments.count(),
            'completed': assignments.filter(status='SUBMITTED').count(),
            'pending': assignments.filter(status__in=['NOT_STARTED', 'IN_PROGRESS']).count(),
            'graded': assignments.filter(status='GRADED').count()
        }
    }
    
    print(f"Returning {len(response_data['assignments'])} assignments to frontend")
    return Response(response_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_logout(request):
    """Student logout endpoint"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Successfully logged out'}, status=200)
    except Exception as e:
        return Response({'detail': 'Logout failed'}, status=400)