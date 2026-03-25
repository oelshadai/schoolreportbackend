from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Teacher
from .serializers import TeacherSerializer, TeacherCreateSerializer
from schools.models import Class, ClassSubject
from students.models import Student, DailyAttendance
from datetime import date
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class CORSPermission(permissions.BasePermission):
    """
    Custom permission that allows OPTIONS requests (for CORS preflight)
    but requires authentication for other methods
    """
    def has_permission(self, request, view):
        # Always allow OPTIONS requests for CORS
        if request.method == 'OPTIONS':
            return True
        # For all other methods, check if user is authenticated
        if request.user and request.user.is_authenticated:
            return True
        # If not authenticated, still return True but let the view handle the logic
        # This prevents blocking at the permission level
        return True

# Function-based view as alternative to action decorator
@api_view(['GET'])
@permission_classes([CORSPermission])
def teacher_assignments_view(request):
    """Get current user's teaching assignments (classes and subjects) with assignment counts"""
    try:
        user = request.user
        results = []
        
        # Check if user is authenticated
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user has school
        if not hasattr(user, 'school') or not user.school:
            return Response([])
        
        # Get classes where user is class teacher
        from schools.models import Class
        class_assignments = Class.objects.filter(
            school=user.school,
            class_teacher=user
        ).select_related('school')
        
        logger.info(f"Found {class_assignments.count()} class assignments for user {user.id}")
        
        for cls in class_assignments:
            results.append({
                'id': f'class_{cls.id}',
                'type': 'form_class',
                'class': {
                    'id': cls.id,
                    'name': str(cls),
                    'level': cls.level,
                    'section': cls.section or ''
                },
                'subject': None,
                'assignment_count': 0
            })
        
        # Get subject assignments
        subject_assignments = ClassSubject.objects.filter(
            teacher=user,
            class_instance__school=user.school
        ).select_related('class_instance', 'subject')
        
        logger.info(f"Found {subject_assignments.count()} subject assignments for user {user.id}")
        
        for assignment in subject_assignments:
            results.append({
                'id': assignment.id,
                'type': 'subject_class',
                'class': {
                    'id': assignment.class_instance.id,
                    'name': str(assignment.class_instance),
                    'level': assignment.class_instance.level,
                    'section': assignment.class_instance.section or ''
                },
                'subject': {
                    'id': assignment.subject.id,
                    'name': assignment.subject.name
                },
                'assignment_count': 0
            })
        
        logger.info(f"Returning {len(results)} total assignments")
        return Response(results)
        
    except Exception as e:
        logger.error(f"ERROR in assignments endpoint: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class TeacherViewSet(viewsets.ModelViewSet):
    """Teacher CRUD operations"""
    queryset = Teacher.objects.all()
    permission_classes = [CORSPermission]
    
    def get_serializer_class(self):
        """Get appropriate serializer based on action"""
        try:
            if self.action == 'create':
                from .serializers import TeacherCreateSerializer
                return TeacherCreateSerializer
            from .serializers import TeacherSerializer
            return TeacherSerializer
        except Exception as e:
            # Fallback to basic serializer
            from .serializers import TeacherSerializer
            return TeacherSerializer
    
    def list(self, request, *args, **kwargs):
        """List teachers - requires authentication"""
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required to list teachers',
                'detail': 'Please login to access teacher data'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get teachers for user's school
            if hasattr(request.user, 'school') and request.user.school:
                teachers = Teacher.objects.filter(school=request.user.school)
            else:
                return Response({
                    'error': 'No school associated with user',
                    'detail': 'User must be associated with a school to view teachers'
                }, status=status.HTTP_403_FORBIDDEN)
                
            serializer = self.get_serializer(teachers, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve teachers',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def health(self, request):
        """Health check endpoint for teachers API"""
        try:
            from .models import Teacher
            teacher_count = Teacher.objects.count()
            
            return Response({
                'status': 'healthy',
                'endpoint': 'teachers',
                'total_teachers': teacher_count,
                'user_authenticated': request.user.is_authenticated,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'user_role': getattr(request.user, 'role', 'Anonymous'),
                'has_school': hasattr(request.user, 'school') and request.user.school is not None if request.user.is_authenticated else False
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'endpoint': 'teachers',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def assignments(self, request):
        """Get current user's teaching assignments (classes and subjects) with assignment counts"""
        try:
            user = request.user
            results = []
            
            # Check if user has school
            if not user.school:
                return Response([])
            
            # Get classes where user is class teacher - FIXED QUERY
            from schools.models import Class
            class_assignments = Class.objects.filter(
                school=user.school,
                class_teacher=user
            ).select_related('school')
            
            logger.info(f"Found {class_assignments.count()} class assignments for user {user.id}")
            
            for cls in class_assignments:
                results.append({
                    'id': f'class_{cls.id}',
                    'type': 'form_class',
                    'class': {
                        'id': cls.id,
                        'name': str(cls),
                        'level': cls.level,
                        'section': cls.section or ''
                    },
                    'subject': None,
                    'assignment_count': 0
                })
            
            # Get subject assignments
            subject_assignments = ClassSubject.objects.filter(
                teacher=user,
                class_instance__school=user.school
            ).select_related('class_instance', 'subject')
            
            logger.info(f"Found {subject_assignments.count()} subject assignments for user {user.id}")
            
            for assignment in subject_assignments:
                results.append({
                    'id': assignment.id,
                    'type': 'subject_class',
                    'class': {
                        'id': assignment.class_instance.id,
                        'name': str(assignment.class_instance),
                        'level': assignment.class_instance.level,
                        'section': assignment.class_instance.section or ''
                    },
                    'subject': {
                        'id': assignment.subject.id,
                        'name': assignment.subject.name
                    },
                    'assignment_count': 0
                })
            
            logger.info(f"Returning {len(results)} total assignments")
            return Response(results)
            
        except Exception as e:
            logger.error(f"ERROR in assignments endpoint: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['get', 'patch'])
    def profile(self, request):
        """Get or update current teacher's profile"""
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get teacher profile for current user
            teacher = Teacher.objects.get(user=request.user)
            
            if request.method == 'GET':
                serializer = TeacherSerializer(teacher)
                return Response(serializer.data)
            
            elif request.method == 'PATCH':
                # Update profile data
                user_data = {}
                teacher_data = {}
                
                # Extract user fields
                if 'first_name' in request.data:
                    user_data['first_name'] = request.data['first_name']
                if 'last_name' in request.data:
                    user_data['last_name'] = request.data['last_name']
                if 'phone_number' in request.data:
                    user_data['phone_number'] = request.data['phone_number']
                
                # Extract teacher fields
                if 'emergency_contact' in request.data:
                    teacher_data['emergency_contact'] = request.data['emergency_contact']
                if 'address' in request.data:
                    teacher_data['address'] = request.data['address']
                if 'qualification' in request.data:
                    teacher_data['qualification'] = request.data['qualification']
                
                # Update user data
                if user_data:
                    for key, value in user_data.items():
                        setattr(teacher.user, key, value)
                    teacher.user.save()
                
                # Update teacher data
                if teacher_data:
                    for key, value in teacher_data.items():
                        setattr(teacher, key, value)
                    teacher.save()
                
                # Return updated profile
                serializer = TeacherSerializer(teacher)
                return Response(serializer.data)
                
        except Teacher.DoesNotExist:
            return Response({
                'error': 'Teacher profile not found',
                'detail': 'No teacher profile associated with this user'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to process profile request',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get teacher dashboard statistics including assignment counts"""
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        user = request.user
        
        # Import required models
        from assignments.models import Assignment, StudentAssignment
        from students.models import DailyAttendance
        from datetime import date, timedelta
        
        # Get teacher's classes (both as class teacher and subject teacher)
        class_teacher_classes = Class.objects.filter(
            school=user.school,
            class_teacher=user
        )
        
        subject_classes = ClassSubject.objects.filter(
            teacher=user
        ).values_list('class_instance', flat=True).distinct()
        
        all_class_ids = list(class_teacher_classes.values_list('id', flat=True)) + list(subject_classes)
        all_class_ids = list(set(all_class_ids))  # Remove duplicates
        
        # Get assignment statistics
        teacher_assignments = Assignment.objects.filter(
            models.Q(created_by=user) |
            models.Q(class_instance__in=all_class_ids)
        ).distinct()
        
        total_assignments = teacher_assignments.count()
        published_assignments = teacher_assignments.filter(status='PUBLISHED').count()
        draft_assignments = teacher_assignments.filter(status='DRAFT').count()
        
        # Get submission statistics
        total_submissions = StudentAssignment.objects.filter(
            assignment__in=teacher_assignments,
            status__in=['SUBMITTED', 'GRADED']
        ).count()
        
        pending_grading = StudentAssignment.objects.filter(
            assignment__in=teacher_assignments,
            status='SUBMITTED'
        ).count()
        
        # Get attendance statistics for today
        today = date.today()
        today_attendance = DailyAttendance.objects.filter(
            class_instance__in=all_class_ids,
            date=today
        )
        
        present_today = today_attendance.filter(status='present').count()
        absent_today = today_attendance.filter(status='absent').count()
        
        return Response({
            'assignments': {
                'total': total_assignments,
                'published': published_assignments,
                'draft': draft_assignments,
                'submissions': total_submissions,
                'pending_grading': pending_grading
            },
            'attendance': {
                'present_today': present_today,
                'absent_today': absent_today,
                'total_today': present_today + absent_today
            },
            'classes': {
                'total_classes': len(all_class_ids),
                'as_class_teacher': class_teacher_classes.count(),
                'as_subject_teacher': len(subject_classes)
            }
        })
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Teacher.objects.all()
        elif user.school:
            return Teacher.objects.filter(school=user.school)
        return Teacher.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TeacherCreateSerializer
        return TeacherSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new teacher with user account"""
        try:
            # Check authentication first
            if not request.user.is_authenticated:
                return Response({
                    'error': 'Authentication required',
                    'detail': 'Please login to create teachers'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if user has school
            if not hasattr(request.user, 'school') or not request.user.school:
                return Response({
                    'error': 'No school associated',
                    'detail': 'User must be associated with a school to create teachers'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check permissions
            if not (getattr(request.user, 'is_school_admin', False) or getattr(request.user, 'is_principal', False)):
                return Response({
                    "error": "Only school admins and principals can create teachers",
                    "detail": f"Current user role: {getattr(request.user, 'role', 'Unknown')}"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Pass context to serializer for validation
            serializer = self.get_serializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                # Set school from user's school
                teacher = serializer.save(school=request.user.school)
                
                # Prepare response with teacher data
                from .serializers import TeacherSerializer
                response_data = TeacherSerializer(teacher).data
                
                # Add login credentials to response
                response_data['login_credentials'] = {
                    'email': teacher.user.email,
                    'password': getattr(teacher, '_plain_password', 'Password was set during creation'),
                    'login_url': '/login',
                    'note': 'Use EMAIL as username, not employee ID'
                }
                
                if hasattr(teacher, '_assigned_class') and teacher._assigned_class:
                    response_data['assigned_class'] = {
                        'id': teacher._assigned_class.id,
                        'name': str(teacher._assigned_class)
                    }
                
                response_data['message'] = f"Teacher {teacher.get_full_name()} created successfully! Login credentials are provided below."
                
                return Response(
                    response_data, 
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': 'Failed to create teacher',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def teaching_schedule(self, request, pk=None):
        """Get teacher's complete teaching schedule"""
        teacher = self.get_object()
        
        # Get classes where teacher is class teacher
        class_teacher_classes = teacher.get_assigned_classes()
        
        # Get subjects teacher is assigned to teach
        teaching_subjects = teacher.get_teaching_subjects()
        
        data = {
            'teacher': TeacherSerializer(teacher).data,
            'class_teacher_for': [
                {
                    'id': cls.id,
                    'name': str(cls),
                    'level': cls.get_level_display(),
                    'section': cls.section,
                    'student_count': cls.students.filter(is_active=True).count()
                }
                for cls in class_teacher_classes
            ],
            'teaching_subjects': [
                {
                    'id': cs.id,
                    'subject_name': cs.subject.name,
                    'class_name': str(cs.class_instance),
                    'class_id': cs.class_instance.id,
                    'subject_id': cs.subject.id
                }
                for cs in teaching_subjects
            ]
        }
        
        return Response(data)
    
    @action(detail=True, methods=['patch'])
    def assign_as_class_teacher(self, request, pk=None):
        """Assign teacher as class teacher to a class"""
        teacher = self.get_object()
        class_id = request.data.get('class_id')
        
        if not class_id:
            return Response(
                {"error": "class_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_class = Class.objects.get(id=class_id, school=teacher.school)
            
            # Check if class already has a teacher assigned
            if target_class.class_teacher and target_class.class_teacher != teacher.user:
                return Response(
                    {"error": f"Class {target_class} already has a class teacher assigned"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            target_class.class_teacher = teacher.user
            target_class.save()
            
            # Update teacher's is_class_teacher flag
            teacher.is_class_teacher = True
            teacher.save()
            
            return Response({
                "message": f"Teacher {teacher.get_full_name()} assigned as class teacher for {target_class}",
                "class_name": str(target_class)
            })
        except Class.DoesNotExist:
            return Response(
                {"error": "Class not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'])
    def assign_subject(self, request, pk=None):
        """Assign teacher to teach a specific subject in a class"""
        teacher = self.get_object()
        class_subject_id = request.data.get('class_subject_id')
        
        if not class_subject_id:
            return Response(
                {"error": "class_subject_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            class_subject = ClassSubject.objects.get(
                id=class_subject_id, 
                class_instance__school=teacher.school
            )
            
            class_subject.teacher = teacher.user
            class_subject.save()
            
            return Response({
                "message": f"Teacher {teacher.get_full_name()} assigned to teach {class_subject.subject.name} in {class_subject.class_instance}"
            })
        except ClassSubject.DoesNotExist:
            return Response(
                {"error": "Class subject assignment not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get', 'post'])
    def attendance(self, request):
        """Take or view class attendance"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if request.method == 'GET':
            return self._get_attendance(request)
        elif request.method == 'POST':
            return self._take_attendance(request)
    
    def _get_attendance(self, request):
        """Get attendance records for teacher's classes"""
        class_id = request.query_params.get('class_id')
        attendance_date = request.query_params.get('date', str(date.today()))
        
        if not class_id:
            return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify teacher has access to this class
            class_obj = Class.objects.get(id=class_id, school=request.user.school)
            if class_obj.class_teacher != request.user:
                return Response({'error': 'Access denied to this class'}, status=status.HTTP_403_FORBIDDEN)
            
            # Get students in the class
            students = Student.objects.filter(current_class=class_obj, is_active=True)
            
            # Get existing attendance records for the date
            attendance_records = DailyAttendance.objects.filter(
                class_instance=class_obj,
                date=attendance_date
            ).select_related('student')
            
            attendance_dict = {record.student_id: record.status for record in attendance_records}
            
            student_list = []
            for student in students:
                student_list.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': student.get_full_name(),
                    'status': attendance_dict.get(student.id, 'absent')
                })
            
            return Response({
                'class_id': class_id,
                'class_name': str(class_obj),
                'date': attendance_date,
                'students': student_list,
                'total_students': len(student_list)
            })
            
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _take_attendance(self, request):
        """Record attendance for students"""
        class_id = request.data.get('class_id')
        attendance_date = request.data.get('date', str(date.today()))
        attendance_records = request.data.get('attendance', [])
        
        if not class_id or not attendance_records:
            return Response({'error': 'class_id and attendance records are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify teacher has access to this class
            class_obj = Class.objects.get(id=class_id, school=request.user.school)
            if class_obj.class_teacher != request.user:
                return Response({'error': 'Access denied to this class'}, status=status.HTTP_403_FORBIDDEN)
            
            updated_count = 0
            created_count = 0
            
            with transaction.atomic():
                for record in attendance_records:
                    student_id = record.get('student_id')
                    status_value = record.get('status', 'absent')
                    
                    if not student_id:
                        continue
                    
                    # Verify student belongs to this class
                    try:
                        student = Student.objects.get(id=student_id, current_class=class_obj, is_active=True)
                    except Student.DoesNotExist:
                        continue
                    
                    # Create or update attendance record
                    attendance, created = DailyAttendance.objects.update_or_create(
                        student=student,
                        class_instance=class_obj,
                        date=attendance_date,
                        defaults={
                            'status': status_value,
                            'marked_by': request.user
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            
            return Response({
                'message': 'Attendance recorded successfully',
                'created': created_count,
                'updated': updated_count,
                'date': attendance_date,
                'class_name': str(class_obj)
            })
            
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)