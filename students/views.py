from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import Student, Attendance, Behaviour, StudentPromotion
from .serializers import (
    StudentSerializer, StudentCreateSerializer, AttendanceSerializer,
    BehaviourSerializer, StudentPromotionSerializer, BulkStudentUploadSerializer
)


class StudentViewSet(viewsets.ModelViewSet):
    """Student CRUD operations"""
    queryset = Student.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentCreateSerializer
        return StudentSerializer
    
    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'school', None):
            return Student.objects.none()

        queryset = Student.objects.filter(school=user.school)

        # Teachers can see students in classes they teach
        if getattr(user, 'role', None) == 'TEACHER':
            from schools.models import ClassSubject, Class
            # Get classes where user is class teacher OR subject teacher
            class_teacher_classes = Class.objects.filter(
                school=user.school,
                class_teacher=user
            ).values_list('id', flat=True)
            subject_classes = ClassSubject.objects.filter(
                teacher=user
            ).values_list('class_instance_id', flat=True)
            teacher_classes = list(class_teacher_classes) + list(subject_classes)
            queryset = queryset.filter(current_class_id__in=teacher_classes)

        # Filter by class if provided
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(current_class_id=class_id)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset
    
    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, 'school', None):
            raise permissions.PermissionDenied("User is not attached to a school")

        # If teacher, ensure they can only create for their own class
        if getattr(user, 'role', None) == 'TEACHER':
            from schools.models import Class
            teacher_classes = list(user.assigned_classes.all())
            if not teacher_classes:
                raise permissions.PermissionDenied("You are not assigned as class teacher to any class")

            payload_class_id = self.request.data.get('current_class') or self.request.data.get('current_class_id')

            if payload_class_id:
                try:
                    cls = Class.objects.get(id=payload_class_id, school=user.school)
                except Class.DoesNotExist:
                    raise permissions.PermissionDenied("Invalid class for this school")
                if cls.class_teacher_id != user.id:
                    raise permissions.PermissionDenied("You can only add students to your assigned class")
                serializer.save(school=user.school)
            else:
                # Auto-assign if teacher has exactly one class; otherwise require explicit selection
                if len(teacher_classes) == 1:
                    serializer.save(school=user.school, current_class=teacher_classes[0])
                else:
                    raise permissions.PermissionDenied("Please choose a class to add the student to")
        else:
            # Admin/Principal can create for any class within their school
            serializer.save(school=user.school)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        if getattr(user, 'role', None) == 'TEACHER':
            # Teachers can only modify students in their own class
            if instance.current_class is None or instance.current_class.class_teacher_id != user.id:
                raise permissions.PermissionDenied("You can only edit students in your assigned class")
            # If changing class, ensure new class is still theirs
            new_class = serializer.validated_data.get('current_class')
            if new_class and new_class.class_teacher_id != user.id:
                raise permissions.PermissionDenied("You can only move students within your assigned class")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if getattr(user, 'role', None) == 'TEACHER':
            # Prevent teachers from deleting students entirely
            raise permissions.PermissionDenied("Teachers cannot delete student records")
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Bulk upload students from Excel file"""
        serializer = BulkStudentUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        excel_file = request.FILES['file']
        
        try:
            try:
                import openpyxl
            except Exception as e:
                return Response(
                    {"error": "openpyxl is not installed. Please add 'openpyxl' to requirements to enable bulk upload."},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            workbook = openpyxl.load_workbook(excel_file)
            sheet = workbook.active
            
            students_created = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    try:
                        # Expected columns: student_id, first_name, last_name, other_names, gender, 
                        # date_of_birth, current_class_id, guardian_name, guardian_phone, 
                        # guardian_email, guardian_address, admission_date
                        
                        student_data = {
                            'school': request.user.school,
                            'student_id': row[0],
                            'first_name': row[1],
                            'last_name': row[2],
                            'other_names': row[3] or '',
                            'gender': row[4],
                            'date_of_birth': row[5],
                            'current_class_id': row[6],
                            'guardian_name': row[7],
                            'guardian_phone': row[8],
                            'guardian_email': row[9] or '',
                            'guardian_address': row[10],
                            'admission_date': row[11],
                        }
                        
                        Student.objects.create(**student_data)
                        students_created += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                "message": f"Successfully created {students_created} students",
                "errors": errors
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to process file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def promote_students(self, request):
        """Promote multiple students to next class"""
        student_ids = request.data.get('student_ids', [])
        to_class_id = request.data.get('to_class_id')
        academic_year_id = request.data.get('academic_year_id')
        
        if not student_ids or not to_class_id or not academic_year_id:
            return Response(
                {"error": "student_ids, to_class_id, and academic_year_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        promoted_count = 0
        
        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id, school=request.user.school)
                    from_class = student.current_class
                    
                    # Create promotion record
                    StudentPromotion.objects.create(
                        student=student,
                        from_class=from_class,
                        to_class_id=to_class_id,
                        academic_year_id=academic_year_id
                    )
                    
                    # Update student's current class
                    student.current_class_id = to_class_id
                    student.save()
                    
                    promoted_count += 1
                    
                except Student.DoesNotExist:
                    continue
        
        return Response({
            "message": f"Successfully promoted {promoted_count} students"
        })


class AttendanceViewSet(viewsets.ModelViewSet):
    """Attendance management"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = Attendance.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            return queryset
        return Attendance.objects.none()


class BehaviourViewSet(viewsets.ModelViewSet):
    """Behaviour/Conduct management"""
    queryset = Behaviour.objects.all()
    serializer_class = BehaviourSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = Behaviour.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            return queryset
        return Behaviour.objects.none()


class StudentPromotionViewSet(viewsets.ReadOnlyModelViewSet):
    """Student promotion history"""
    queryset = StudentPromotion.objects.all()
    serializer_class = StudentPromotionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return StudentPromotion.objects.filter(student__school=user.school)
        return StudentPromotion.objects.none()
