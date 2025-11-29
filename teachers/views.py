from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Teacher
from .serializers import TeacherSerializer, TeacherCreateSerializer
from schools.models import Class, ClassSubject

User = get_user_model()


class TeacherViewSet(viewsets.ModelViewSet):
    """Teacher CRUD operations"""
    queryset = Teacher.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def assignments(self, request):
        """Get current user's teaching assignments (classes and subjects)"""
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
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check permissions
            if not (request.user.is_school_admin or request.user.is_principal):
                return Response(
                    {"error": "Only school admins and principals can create teachers"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Set school from user's school
            teacher = serializer.save(school=request.user.school)
            
            return Response(
                TeacherSerializer(teacher).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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