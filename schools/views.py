from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import School, AcademicYear, Term, Class, Subject, ClassSubject, GradingScale
from .serializers import (
    SchoolSerializer, AcademicYearSerializer, TermSerializer,
    ClassSerializer, SubjectSerializer, ClassSubjectSerializer,
    GradingScaleSerializer, BulkAssignmentSerializer, BulkRemovalSerializer,
    SchoolSettingsSerializer
)
from django.contrib.auth import get_user_model
from students.models import Student
from reports.models import ReportCard
from django.db import models
from django.db.models import Count

User = get_user_model()


class SchoolViewSet(viewsets.ModelViewSet):
    """School CRUD operations"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Prevent conflicts with nested routes like /api/schools/classes/ by ensuring
    # the detail lookup only matches numeric IDs (e.g., /api/schools/123/)
    lookup_value_regex = r"\d+"
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return School.objects.all()
        elif user.school:
            return School.objects.filter(id=user.school.id)
        return School.objects.none()
    
    @action(detail=True, methods=['post'])
    def setup_default_subjects(self, request, pk=None):
        """Setup default subjects for a school"""
        school = self.get_object()
        
        # Default subjects will be created via management command or admin
        return Response({"message": "Default subjects setup initiated"})


class AcademicYearViewSet(viewsets.ModelViewSet):
    """Academic Year operations"""
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return AcademicYear.objects.filter(school=user.school)
        return AcademicYear.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class TermViewSet(viewsets.ModelViewSet):
    """Term operations"""
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Term.objects.filter(academic_year__school=user.school)
        return Term.objects.none()
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """Set a term as current"""
        term = self.get_object()
        Term.objects.filter(academic_year__school=request.user.school).update(is_current=False)
        term.is_current = True
        term.save()
        return Response({"message": "Term set as current"})


class ClassViewSet(viewsets.ModelViewSet):
    """Class operations"""
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Class.objects.filter(school=user.school)
        return Class.objects.none()
    
    def perform_create(self, serializer):
        if not getattr(self.request.user, 'school', None):
            raise permissions.PermissionDenied("User is not attached to a school")
        serializer.save(school=self.request.user.school)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students in a class"""
        class_instance = self.get_object()
        students = class_instance.students.filter(is_active=True)
        from students.serializers import StudentSerializer
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_level(self, request):
        """Get classes filtered by level group (primary/jhs)"""
        level_group = request.query_params.get('level_group', '').upper()
        user = request.user
        
        if user.school:
            queryset = Class.objects.filter(school=user.school)
            
            if level_group == 'PRIMARY':
                # Basic 1-6
                queryset = queryset.filter(level__in=[
                    'BASIC_1', 'BASIC_2', 'BASIC_3', 'BASIC_4', 'BASIC_5', 'BASIC_6'
                ])
            elif level_group == 'JHS':
                # Basic 7-9
                queryset = queryset.filter(level__in=[
                    'BASIC_7', 'BASIC_8', 'BASIC_9'
                ])
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response([])


class SubjectViewSet(viewsets.ModelViewSet):
    """Subject operations"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClassSubjectViewSet(viewsets.ModelViewSet):
    """Class Subject assignment"""
    queryset = ClassSubject.objects.all()
    serializer_class = ClassSubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            qs = ClassSubject.objects.filter(class_instance__school=user.school)
            # Teachers can only see assignments for classes they are class_teacher (owner) or where they are set as teacher for the subject
            if user.role == 'TEACHER':
                qs = qs.filter(models.Q(class_instance__class_teacher=user) | models.Q(teacher=user))
            class_id = self.request.query_params.get('class_instance')
            if class_id:
                qs = qs.filter(class_instance_id=class_id)
            subject_id = self.request.query_params.get('subject')
            if subject_id:
                qs = qs.filter(subject_id=subject_id)
            return qs
        return ClassSubject.objects.none()

    def _ensure_teacher_class_permission(self, class_obj: Class):
        user = self.request.user
        if user.role == 'TEACHER' and class_obj.class_teacher_id != user.id:
            raise permissions.PermissionDenied("You can only manage subjects for your own class")

    def perform_create(self, serializer):
        user = self.request.user
        class_id = self.request.data.get('class_instance')
        try:
            class_obj = Class.objects.get(id=class_id, school=user.school)
        except Class.DoesNotExist:
            raise permissions.PermissionDenied("Invalid class for this school")
        self._ensure_teacher_class_permission(class_obj)
        if user.role == 'TEACHER':
            # Teachers cannot introduce new subjects; admin/principal must pre-populate
            raise permissions.PermissionDenied("Teachers cannot add new subjects. Admin must assign them first.")
        # Category compatibility: PRIMARY subjects only for Basic 1-6; JHS only for Basic 7-9; BOTH allowed everywhere
        subject_id = self.request.data.get('subject')
        try:
            subject_obj = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise permissions.PermissionDenied("Invalid subject")
        level = class_obj.level
        is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
        is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
        if subject_obj.category == 'PRIMARY' and not is_primary_level:
            raise permissions.PermissionDenied("Subject is for primary classes only")
        if subject_obj.category == 'JHS' and not is_jhs_level:
            raise permissions.PermissionDenied("Subject is for JHS classes only")
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        self._ensure_teacher_class_permission(instance.class_instance)
        # Optional: ensure updated subject still matches category if subject changed
        new_subject = serializer.validated_data.get('subject')
        if new_subject:
            level = instance.class_instance.level
            is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
            is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
            if new_subject.category == 'PRIMARY' and not is_primary_level:
                raise permissions.PermissionDenied("Subject is for primary classes only")
            if new_subject.category == 'JHS' and not is_jhs_level:
                raise permissions.PermissionDenied("Subject is for JHS classes only")
        user = self.request.user
        if user.role == 'TEACHER':
            # Teachers can only claim or unclaim (set teacher to self or null). They cannot change subject or class.
            disallowed_keys = {'class_instance', 'subject'} & set(serializer.validated_data.keys())
            if disallowed_keys:
                raise permissions.PermissionDenied("Teachers cannot modify subject or class; only claim/unclaim.")
            teacher_obj = serializer.validated_data.get('teacher')
            if teacher_obj and teacher_obj.id != user.id:
                raise permissions.PermissionDenied("You can only claim a subject for yourself.")
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_teacher_class_permission(instance.class_instance)
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """Bulk assign subjects to multiple classes"""
        user = request.user
        if user.role == 'TEACHER':
            return Response(
                {"detail": "Teachers cannot perform bulk operations"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        subject_ids = serializer.validated_data['subject_ids']
        class_ids = serializer.validated_data['class_ids']
        
        # Validate subjects exist and get them
        subjects = Subject.objects.filter(id__in=subject_ids)
        if len(subjects) != len(subject_ids):
            return Response(
                {"detail": "Some subjects not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate classes exist and belong to user's school
        classes = Class.objects.filter(id__in=class_ids, school=user.school)
        if len(classes) != len(class_ids):
            return Response(
                {"detail": "Some classes not found or don't belong to your school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_assignments = []
        skipped_assignments = []
        invalid_assignments = []
        
        for class_obj in classes:
            for subject in subjects:
                # Check category compatibility
                level = class_obj.level
                is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
                is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
                
                if subject.category == 'PRIMARY' and not is_primary_level:
                    invalid_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Subject is for primary classes only'
                    })
                    continue
                if subject.category == 'JHS' and not is_jhs_level:
                    invalid_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Subject is for JHS classes only'
                    })
                    continue
                
                # Check if assignment already exists
                if ClassSubject.objects.filter(class_instance=class_obj, subject=subject).exists():
                    skipped_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Already assigned'
                    })
                    continue
                
                # Create assignment
                assignment = ClassSubject.objects.create(
                    class_instance=class_obj,
                    subject=subject
                )
                created_assignments.append({
                    'id': assignment.id,
                    'class': str(class_obj),
                    'subject': subject.name
                })
        
        return Response({
            'created': created_assignments,
            'skipped': skipped_assignments,
            'invalid': invalid_assignments,
            'summary': {
                'created_count': len(created_assignments),
                'skipped_count': len(skipped_assignments),
                'invalid_count': len(invalid_assignments)
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_remove(self, request):
        """Bulk remove subjects from multiple classes"""
        user = request.user
        if user.role == 'TEACHER':
            return Response(
                {"detail": "Teachers cannot perform bulk operations"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkRemovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        subject_ids = serializer.validated_data['subject_ids']
        class_ids = serializer.validated_data['class_ids']
        
        # Get assignments to remove
        assignments = ClassSubject.objects.filter(
            class_instance__id__in=class_ids,
            subject__id__in=subject_ids,
            class_instance__school=user.school
        )
        
        removed_assignments = []
        for assignment in assignments:
            removed_assignments.append({
                'class': str(assignment.class_instance),
                'subject': assignment.subject.name
            })
        
        assignments.delete()
        
        return Response({
            'removed': removed_assignments,
            'summary': {
                'removed_count': len(removed_assignments)
            }
        })


class GradingScaleViewSet(viewsets.ModelViewSet):
    """Grading Scale operations"""
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return GradingScale.objects.filter(school=user.school)
        return GradingScale.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class SchoolDashboardView(APIView):
    """Return dashboard metrics for the current user's school"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not getattr(user, 'school', None):
            return Response({"detail": "User is not attached to a school"}, status=status.HTTP_403_FORBIDDEN)

        school = user.school
        # Counts
        students_count = Student.objects.filter(school=school).count()
        teachers_count = User.objects.filter(school=school, role='TEACHER').count()
        classes_count = Class.objects.filter(school=school).count()
        subjects_count = Subject.objects.filter(assigned_classes__class_instance__school=school).distinct().count()
        reports_count = ReportCard.objects.filter(student__school=school).count()

        # Current AY/Term
        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(academic_year__school=school, is_current=True).first()

        # Chart data: Students per class
        classes = Class.objects.filter(school=school).annotate(student_count=Count('students'))
        students_by_class = [
            {"name": f"{c.get_level_display() or c.level}{' ' + c.section if c.section else ''}", "students": c.student_count}
            for c in classes
        ]

        # Chart data: Gender distribution
        gender_dist = Student.objects.filter(school=school).values('gender').annotate(count=Count('id'))
        gender_data = [{"name": item['gender'], "value": item['count']} for item in gender_dist]

        # Chart data: Subjects by category
        subject_category_dist = Subject.objects.filter(
            assigned_classes__class_instance__school=school
        ).values('category').annotate(count=Count('id', distinct=True))
        subjects_by_category = [{"name": item['category'], "value": item['count']} for item in subject_category_dist]

        data = {
            "school": {
                "id": school.id, 
                "name": school.name,
                "score_entry_mode": school.score_entry_mode,
                "report_template": school.report_template,
                "show_class_average": school.show_class_average,
                "show_position_in_class": school.show_position_in_class,
            },
            "counts": {
                "students": students_count,
                "teachers": teachers_count,
                "classes": classes_count,
                "subjects": subjects_count,
                "reports": reports_count,
            },
            "current": {
                "academic_year": current_year.name if current_year else None,
                "term": current_term.get_name_display() if current_term else None,
            },
            "charts": {
                "students_by_class": students_by_class,
                "gender_distribution": gender_data,
                "subjects_by_category": subjects_by_category,
            }
        }
        return Response(data)


class SchoolSettingsView(APIView):
    """Manage school settings and configuration"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current school settings"""
        user = request.user
        if not user.school:
            return Response(
                {"error": "User is not associated with a school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SchoolSettingsSerializer(user.school)
        return Response(serializer.data)
    
    def patch(self, request):
        """Update school settings"""
        user = request.user
        if not user.school:
            return Response(
                {"error": "User is not associated with a school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has permission to modify school settings
        if not (user.is_super_admin or user.is_school_admin):
            return Response(
                {"error": "You don't have permission to modify school settings"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SchoolSettingsSerializer(
            user.school, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "School settings updated successfully",
                "data": serializer.data
            })
        
        # Add debug logging
        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
