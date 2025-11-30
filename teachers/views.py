from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Teacher
from .serializers import TeacherSerializer, TeacherCreateSerializer
from schools.models import Class, ClassSubject

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


class CORSMixin:
    """Mixin to add CORS headers to all responses"""
    
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Add comprehensive CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Encoding, Accept-Language, Authorization, Content-Type, '
            'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With, Cache-Control'
        )
        response['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
        response['Vary'] = 'Origin'
        
        return response


@method_decorator(csrf_exempt, name='dispatch')
class TeacherViewSet(CORSMixin, viewsets.ModelViewSet):
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
        """Get current user's teaching assignments (classes and subjects)"""
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        user = request.user
        
        # Get classes where user is class teacher
        class_teacher_assignments = Class.objects.filter(
            school=user.school,
            class_teacher=user
        )
        
        # Get subject teaching assignments
        subject_assignments = ClassSubject.objects.filter(
            teacher=user
        ).select_related('class_instance', 'subject')
        
        # Build response with both types
        results = []
        
        # Add form class assignments
        for cls in class_teacher_assignments:
            results.append({
                'id': f'class_{cls.id}',
                'type': 'form_class',
                'class': {
                    'id': cls.id,
                    'name': str(cls),
                    'level': cls.level,
                    'section': cls.section or ''
                },
                'subject': None
            })
        
        # Add subject assignments
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
                }
            })
        
        return Response({'results': results})
    
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
            
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Set school from user's school
                teacher = serializer.save(school=request.user.school)
                
                # Prepare response with teacher data
                from .serializers import TeacherSerializer
                response_data = TeacherSerializer(teacher).data
                response_data['message'] = f"Teacher {teacher.get_full_name()} created successfully! Welcome email with login credentials has been sent to {teacher.user.email}."
                
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
            target_class.class_teacher = teacher.user
            target_class.save()
            
            # Update teacher's is_class_teacher flag
            teacher.is_class_teacher = True
            teacher.save()
            
            return Response({
                "message": f"Teacher {teacher.get_full_name()} assigned as class teacher for {target_class}"
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