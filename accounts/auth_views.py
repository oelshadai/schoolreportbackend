from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import status
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    try:
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({
                'error': 'Current password and new password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Verify current password
        if not user.check_password(current_password):
            return Response({
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password length
        if len(new_password) < 8:
            return Response({
                'error': 'New password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception(f"Change password error: {str(e)}")
        return Response({
            'error': 'Failed to change password'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def teacher_login(request):
    """Teacher login endpoint"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password required'},
                status=400
            )

        email = str(email).strip().lower()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # Check role is teacher or admin
        if user.role not in ['TEACHER', 'PRINCIPAL', 'SCHOOL_ADMIN']:
            return Response({'error': 'Invalid credentials'}, status=401)

        # Verify password
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=401)

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
        except Exception as e:
            logger.error(f"Token generation error for {email}: {str(e)}")
            return Response({'error': 'Token generation failed'}, status=500)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'role': user.role,
                'phone_number': user.phone_number or '',
                'school_id': user.school.id if user.school else None
            }
        }, status=200)

    except Exception as e:
        logger.exception(f"Teacher login error: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """School Admin login endpoint"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password required'},
                status=400
            )

        email = str(email).strip().lower()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # Check role is school admin
        if user.role != 'SCHOOL_ADMIN':
            return Response({'error': 'Invalid credentials'}, status=401)

        # Verify password
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=401)

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
        except Exception as e:
            logger.error(f"Token generation error for {email}: {str(e)}")
            return Response({'error': 'Token generation failed'}, status=500)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'role': user.role,
                'phone_number': user.phone_number or '',
                'school_id': user.school.id if user.school else None,
                'school_name': user.school.name if user.school else None
            }
        }, status=200)

    except Exception as e:
        logger.exception(f"Admin login error: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def superadmin_login(request):
    """Super Admin login endpoint"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password required'},
                status=400
            )

        email = str(email).strip().lower()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # Check role is super admin
        if user.role != 'SUPER_ADMIN':
            return Response({'error': 'Invalid credentials'}, status=401)

        # Verify password
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=401)

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
        except Exception as e:
            logger.error(f"Token generation error for {email}: {str(e)}")
            return Response({'error': 'Token generation failed'}, status=500)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'role': user.role,
                'phone_number': user.phone_number or ''
            }
        }, status=200)

    except Exception as e:
        logger.exception(f"Super Admin login error: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard(request):
    """Teacher dashboard with real data"""
    try:
        from teachers.models import Teacher
        try:
            teacher = Teacher.objects.select_related('user', 'school').get(user=request.user)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher profile not found'}, status=404)

        # Get assigned classes safely - FIXED QUERY
        try:
            # Direct query to ensure we get the correct classes
            from schools.models import Class
            assigned_classes = Class.objects.filter(
                class_teacher=request.user,
                school=teacher.school
            ).select_related('school')
            
            logger.info(f"Teacher {teacher.id} ({teacher.user.email}) - Found {assigned_classes.count()} assigned classes")
            
            # Debug: Log the actual classes found
            for cls in assigned_classes:
                logger.info(f"  - Class: {cls} (ID: {cls.id}, Teacher: {cls.class_teacher_id}, User: {request.user.id})")
            
            classes_data = [{
                'id': c.id,
                'name': str(c),  # Use __str__ method which handles section properly
                'level': c.get_level_display(),
                'students_count': c.students.filter(is_active=True).count()
            } for c in assigned_classes]
            
            logger.info(f"Classes data prepared: {classes_data}")
        except Exception as e:
            logger.error(f"Error getting assigned classes for teacher {teacher.id}: {str(e)}")
            classes_data = []

        # Get teaching subjects safely
        try:
            teaching_subjects = teacher.get_teaching_subjects()
            logger.info(f"Found {teaching_subjects.count()} teaching subjects for teacher {teacher.id}")
            subjects_data = []
            for cs in teaching_subjects:
                try:
                    subjects_data.append({
                        'id': cs.id,
                        'subject': cs.subject.name if cs.subject else 'Unknown',
                        'class': str(cs.class_instance) if cs.class_instance else 'Unknown',
                        'class_id': cs.class_instance.id if getattr(cs, 'class_instance', None) and getattr(cs.class_instance, 'id', None) else None
                    })
                except Exception as e:
                    logger.warning(f"Error processing class subject {cs.id}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error getting teaching subjects for teacher {teacher.id}: {str(e)}")
            subjects_data = []

        # Get attendance count for today - FIXED
        try:
            from students.models import DailyAttendance
            from datetime import date
            today = date.today()
            
            # Count classes where teacher has taken attendance today
            attendance_count = 0
            for cls in assigned_classes:
                if DailyAttendance.objects.filter(
                    class_instance=cls,
                    date=today,
                    marked_by=request.user
                ).exists():
                    attendance_count += 1
                    
        except Exception as e:
            logger.error(f"Error getting attendance count for teacher {teacher.id}: {str(e)}")
            attendance_count = 0

        # Get recent announcements for teachers
        try:
            from announcements.models import Announcement
            announcements = Announcement.objects.filter(
                school=teacher.school,
                audience__in=['ALL', 'TEACHERS']
            ).order_by('-is_pinned', '-created_at')[:5]
            announcements_data = [{
                'id': a.id,
                'title': a.title,
                'content': a.content,
                'created_at': a.created_at.isoformat(),
                'priority': 'high' if a.is_pinned else 'normal'
            } for a in announcements]
        except Exception as e:
            logger.error(f"Error getting announcements for teacher {teacher.id}: {str(e)}")
            announcements_data = []

        # Get assignments count - check multiple possible fields
        try:
            from assignments.models import Assignment
            # Try different possible assignment queries
            assignments_by_user = Assignment.objects.filter(created_by=request.user).count()
            assignments_by_teacher = Assignment.objects.filter(teacher=request.user).count() if hasattr(Assignment, 'teacher') else 0
            assignments_count = max(assignments_by_user, assignments_by_teacher)
            logger.info(f"Found {assignments_count} assignments for teacher {teacher.id}")
        except Exception as e:
            logger.error(f"Error getting assignments count for teacher {teacher.id}: {str(e)}")
            assignments_count = 0

        response_data = {
            'teacher': {
                'id': teacher.id,
                'user_id': teacher.user.id,
                'name': teacher.get_full_name(),
                'first_name': teacher.user.first_name,
                'last_name': teacher.user.last_name,
                'email': teacher.user.email,
                'employee_id': teacher.employee_id,
                'phone_number': teacher.user.phone_number or '',
                'school': teacher.school.name if teacher.school else None,
                'school_id': teacher.school.id if teacher.school else None,
                'qualification': teacher.qualification or '',
                'experience_years': teacher.experience_years or 0,
                'hire_date': teacher.hire_date.isoformat() if teacher.hire_date else None,
                'is_class_teacher': teacher.is_class_teacher,
                'is_active': teacher.is_active,
                'role': 'TEACHER'
            },
            'assigned_classes': classes_data,
            'teaching_subjects': subjects_data,
            'announcements': announcements_data,
            'stats': {
                'total_assignments': assignments_count,
                'total_classes': len(classes_data),
                'total_subjects': len(subjects_data),
                'attendance_taken_today': attendance_count
            }
        }

        return Response(response_data)

    except Exception as e:
        logger.exception(f"Teacher dashboard error: {str(e)}")
        return Response({'error': 'Dashboard error'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    """School Admin dashboard with enhanced stats including attendance"""
    try:
        user = request.user
        school = user.school

        if not school:
            return Response({'error': 'School not assigned'}, status=400)

        try:
            from students.models import Student, Attendance
            from teachers.models import Teacher
            from schools.models import Class, Term
            from assignments.models import Assignment
            from django.db.models import Count, Q, Avg
            from datetime import datetime, timedelta

            # Basic counts
            students_count = Student.objects.filter(school=school, is_active=True).count()
            teachers_count = Teacher.objects.filter(school=school, is_active=True).count()
            classes_count = Class.objects.filter(school=school).count()
            
            # Assignment count
            try:
                assignments_count = Assignment.objects.filter(
                    class_instance__in=Class.objects.filter(school=school)
                ).count()
            except Exception:
                assignments_count = 0

            # Attendance statistics
            current_term = Term.objects.filter(
                academic_year__school=school, 
                is_current=True
            ).first()
            
            attendance_stats = {
                'total_present_today': 0,
                'total_absent_today': 0,
                'attendance_rate': 0,
                'classes_with_low_attendance': 0
            }
            
            if current_term:
                today = datetime.now().date()
                
                # Today's attendance
                today_attendance = Attendance.objects.filter(
                    student__school=school,
                    term=current_term,
                    date=today
                ).aggregate(
                    present=Count('id', filter=Q(status='PRESENT')),
                    absent=Count('id', filter=Q(status='ABSENT'))
                )
                
                attendance_stats['total_present_today'] = today_attendance['present'] or 0
                attendance_stats['total_absent_today'] = today_attendance['absent'] or 0
                
                # Overall attendance rate for current term
                total_attendance_records = Attendance.objects.filter(
                    student__school=school,
                    term=current_term
                ).count()
                
                if total_attendance_records > 0:
                    present_records = Attendance.objects.filter(
                        student__school=school,
                        term=current_term,
                        status='PRESENT'
                    ).count()
                    attendance_stats['attendance_rate'] = round((present_records / total_attendance_records) * 100, 1)
                
                # Classes with low attendance (below 80%)
                classes_with_low_attendance = 0
                for class_obj in Class.objects.filter(school=school):
                    class_attendance = Attendance.objects.filter(
                        student__current_class=class_obj,
                        term=current_term
                    ).aggregate(
                        total=Count('id'),
                        present=Count('id', filter=Q(status='PRESENT'))
                    )
                    
                    if class_attendance['total'] and class_attendance['total'] > 0:
                        class_rate = (class_attendance['present'] / class_attendance['total']) * 100
                        if class_rate < 80:
                            classes_with_low_attendance += 1
                
                attendance_stats['classes_with_low_attendance'] = classes_with_low_attendance

            # Class statistics with student counts and attendance
            class_stats = []
            for class_obj in Class.objects.filter(school=school).select_related('class_teacher'):
                student_count = Student.objects.filter(current_class=class_obj, is_active=True).count()
                
                # Class attendance rate
                class_attendance_rate = 0
                if current_term:
                    class_attendance = Attendance.objects.filter(
                        student__current_class=class_obj,
                        term=current_term
                    ).aggregate(
                        total=Count('id'),
                        present=Count('id', filter=Q(status='PRESENT'))
                    )
                    
                    if class_attendance['total'] and class_attendance['total'] > 0:
                        class_attendance_rate = round((class_attendance['present'] / class_attendance['total']) * 100, 1)
                
                class_stats.append({
                    'id': class_obj.id,
                    'name': class_obj.name,
                    'level': class_obj.level,
                    'student_count': student_count,
                    'class_teacher': class_obj.class_teacher.get_full_name() if class_obj.class_teacher else 'Not Assigned',
                    'attendance_rate': class_attendance_rate
                })

            # Recent students and teachers (same as before)
            recent_students = Student.objects.filter(school=school, is_active=True).order_by('-created_at')[:5]
            recent_teachers = Teacher.objects.filter(school=school, is_active=True).order_by('-created_at')[:5]

            recent_students_data = []
            for s in recent_students:
                try:
                    recent_students_data.append({
                        'id': s.id,
                        'name': s.get_full_name(),
                        'student_id': s.student_id,
                        'class': s.current_class.name if s.current_class else 'Not Assigned'
                    })
                except Exception:
                    continue

            recent_teachers_data = []
            for t in recent_teachers:
                try:
                    recent_teachers_data.append({
                        'id': t.id,
                        'name': t.get_full_name(),
                        'employee_id': t.employee_id,
                        'qualification': t.qualification or 'Not Specified'
                    })
                except Exception:
                    continue

            response_data = {
                'admin': {
                    'id': user.id,
                    'name': user.get_full_name(),
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone_number': user.phone_number or '',
                    'school': school.name if school else None,
                    'school_id': school.id if school else None,
                    'role': 'SCHOOL_ADMIN'
                },
                'school_stats': {
                    'total_students': students_count,
                    'total_teachers': teachers_count,
                    'total_classes': classes_count,
                    'total_assignments': assignments_count
                },
                'attendance_stats': attendance_stats,
                'class_stats': class_stats,
                'recent_students': recent_students_data,
                'recent_teachers': recent_teachers_data
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Admin dashboard data error: {str(e)}")
            return Response({'error': 'Dashboard error'}, status=500)

    except Exception as e:
        logger.exception(f"Admin dashboard error: {str(e)}")
        return Response({'error': 'Dashboard error'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def superadmin_dashboard(request):
    """Super Admin dashboard with system-wide data"""
    if not request.user or not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=401)

    try:
        from schools.models import School
        from students.models import Student
        from teachers.models import Teacher
        from accounts.models import User
        from assignments.models import Assignment

        schools_count = School.objects.count()
        students_count = Student.objects.count()
        teachers_count = Teacher.objects.count()
        admins_count = User.objects.filter(role='SCHOOL_ADMIN').count()
        assignments_count = Assignment.objects.count()

        recent_schools = School.objects.order_by('-created_at')[:5]

        response_data = {
            'superadmin': {
                'id': request.user.id,
                'name': request.user.get_full_name(),
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone_number': request.user.phone_number or '',
                'role': 'SUPER_ADMIN'
            },
            'system_stats': {
                'total_schools': schools_count,
                'total_students': students_count,
                'total_teachers': teachers_count,
                'total_admins': admins_count,
                'total_assignments': assignments_count
            },
            'recent_schools': [{
                'id': s.id,
                'name': s.name,
                'location': s.location,
                'students': Student.objects.filter(school=s).count(),
                'teachers': Teacher.objects.filter(school=s).count()
            } for s in recent_schools]
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Super Admin dashboard error: {str(e)}")
        return Response({'error': 'Dashboard error'}, status=500)
