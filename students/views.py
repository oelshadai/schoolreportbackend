from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.utils.dateparse import parse_date
from .validation import StudentInputValidator, StudentValidationMixin
from .models import Student, Attendance, Behaviour, StudentPromotion, DailyAttendance
from .serializers import (
    StudentSerializer, StudentCreateSerializer, AttendanceSerializer,
    BehaviourSerializer, StudentPromotionSerializer, BulkStudentUploadSerializer,
    DailyAttendanceSerializer, BulkAttendanceSerializer
)


class StudentViewSet(StudentValidationMixin, viewsets.ModelViewSet):
    """Student CRUD operations with security validation"""
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

        # Validate and sanitize student data
        student_data = self.clean_student_input(self.request.data)
        try:
            self.validate_student_data(student_data)
        except Exception as e:
            raise permissions.PermissionDenied(f"Invalid student data: {str(e)}")

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
            # Only class teachers can toggle student status, not subject teachers
            if not instance.current_class or instance.current_class.class_teacher != user:
                raise permissions.PermissionDenied("Only class teachers can manage students in their class")
            # Toggle student active status instead of deleting
            instance.is_active = not instance.is_active
            instance.save()
            return
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

    @action(detail=True, methods=['get'])
    def credentials(self, request, pk=None):
        """Get student portal login credentials"""
        student = self.get_object()
        return Response({
            'student_name': student.get_full_name(),
            'student_id': student.student_id,
            'username': student.username or f"std_{student.student_id}",
            'password': student.password or 'Not available',
            'class_name': student.current_class.full_name if student.current_class else 'No Class',
        })


class DailyAttendanceViewSet(viewsets.ModelViewSet):
    """Daily Attendance management"""
    queryset = DailyAttendance.objects.all()
    serializer_class = DailyAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """List attendance records with proper error handling"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Always return a successful response, even if no records found
            return Response({
                'results': serializer.data,
                'count': len(serializer.data)
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'results': [],
                'count': 0
            }, status=status.HTTP_200_OK)
    
    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'school') or not user.school:
            return DailyAttendance.objects.none()
            
        queryset = DailyAttendance.objects.filter(student__school=user.school)
        
        # Filter by class
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(class_instance_id=class_id)
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
        
        # Filter by student
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset.select_related('student', 'class_instance')
    
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Bulk create/update daily attendance records"""
        serializer = BulkAttendanceSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        records = serializer.validated_data['records']
        created_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for record_data in records:
                try:
                    # Validate required fields
                    student_id = record_data.get('student')
                    class_id = record_data.get('class_instance')
                    date = record_data.get('date')
                    status_value = record_data.get('status', 'absent')
                    
                    if not all([student_id, class_id, date]):
                        errors.append(f"Missing required fields for record: {record_data}")
                        continue
                    
                    # Validate student belongs to user's school
                    try:
                        student = Student.objects.get(
                            id=student_id, 
                            school=request.user.school
                        )
                    except Student.DoesNotExist:
                        errors.append(f"Student {student_id} not found in your school")
                        continue
                    
                    # Create or update attendance record
                    attendance, created = DailyAttendance.objects.update_or_create(
                        student_id=student_id,
                        date=date,
                        defaults={
                            'class_instance_id': class_id,
                            'status': status_value,
                            'marked_by': request.user
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Send notification to student
                    self._send_attendance_notification(student, status_value, date)
                    
                except Exception as e:
                    errors.append(f"Error processing record {record_data}: {str(e)}")
        
        # Notify admins that attendance was taken
        try:
            from notifications.attendance_notifications import notify_admins_attendance_taken
            from schools.models import Class
            from datetime import datetime
            
            if records and created_count > 0:
                # Get class from first record
                first_record = records[0]
                class_obj = Class.objects.get(id=first_record.get('class_instance'))
                date_obj = datetime.strptime(str(first_record.get('date')), '%Y-%m-%d').date()
                
                notify_admins_attendance_taken(
                    school=request.user.school,
                    teacher=request.user,
                    class_obj=class_obj,
                    date=date_obj
                )
        except Exception as e:
            print(f"Failed to notify admins about attendance: {e}")
        
        return Response({
            "message": f"Successfully processed attendance records",
            "created": created_count,
            "updated": updated_count,
            "errors": errors
        }, status=status.HTTP_200_OK)
    
    def _send_attendance_notification(self, student, status, date):
        """Send attendance notification to student"""
        try:
            from notifications.models import Notification
            
            if student.user:
                status_text = "Present" if status == 'present' else "Absent" if status == 'absent' else "Late"
                status_emoji = "✅" if status == 'present' else "❌" if status == 'absent' else "⏰"
                notification_type = 'success' if status == 'present' else 'warning' if status == 'absent' else 'info'
                
                # Create notification
                Notification.objects.create(
                    user=student.user,
                    title=f"{status_emoji} Attendance Update",
                    message=f"Your attendance for {date} has been marked as {status_text}. Check your dashboard for details.",
                    type=notification_type
                )
                
                # Also update term attendance summary
                self._update_term_attendance(student, status, date)
                
                print(f"Attendance notification sent to {student.get_full_name()} for {date}: {status_text}")
                
        except Exception as e:
            # Don't fail attendance saving if notification fails
            print(f"Failed to send notification to student {student.id}: {e}")
    
    def _update_term_attendance(self, student, status, date):
        """Update term-based attendance summary"""
        try:
            from schools.models import Term
            from datetime import datetime
            
            # Find current term for the date
            date_obj = datetime.strptime(str(date), '%Y-%m-%d').date()
            current_term = Term.objects.filter(
                school=student.school,
                start_date__lte=date_obj,
                end_date__gte=date_obj
            ).first()
            
            if current_term:
                attendance_record, created = Attendance.objects.get_or_create(
                    student=student,
                    term=current_term,
                    defaults={'days_present': 0, 'days_absent': 0, 'times_late': 0}
                )
                
                if status == 'present':
                    attendance_record.days_present += 1
                elif status == 'absent':
                    attendance_record.days_absent += 1
                elif status == 'late':
                    attendance_record.times_late += 1
                    attendance_record.days_present += 1  # Late is still present
                
                attendance_record.save()
                
        except Exception as e:
            print(f"Failed to update term attendance for student {student.id}: {e}")
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """Generate attendance reports"""
        user = request.user
        if not hasattr(user, 'school') or not user.school:
            return Response({'error': 'No school associated'}, status=status.HTTP_403_FORBIDDEN)
            
        class_id = request.query_params.get('class_id')
        report_type = request.query_params.get('report_type', 'daily')
        date = request.query_params.get('date')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not class_id:
            return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from django.db.models import Count, Q
            
            queryset = DailyAttendance.objects.filter(
                student__school=user.school,
                class_instance_id=class_id
            )
            
            if report_type == 'daily' and date:
                queryset = queryset.filter(date=date)
            elif report_type == 'weekly' and start_date and end_date:
                queryset = queryset.filter(date__range=[start_date, end_date])
            elif report_type == 'monthly' and start_date and end_date:
                queryset = queryset.filter(date__range=[start_date, end_date])
            
            # Calculate statistics
            total_records = queryset.count()
            present_count = queryset.filter(status='present').count()
            absent_count = queryset.filter(status='absent').count()
            late_count = queryset.filter(status='late').count()
            
            attendance_rate = 0
            if total_records > 0:
                attendance_rate = round((present_count / total_records) * 100, 2)
            
            return Response({
                'total_present': present_count,
                'total_absent': absent_count,
                'total_late': late_count,
                'total_records': total_records,
                'attendance_rate': attendance_rate,
                'report_type': report_type,
                'class_id': class_id,
                'date_range': {
                    'start': start_date or date,
                    'end': end_date or date
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AttendanceViewSet(viewsets.ModelViewSet):
    """Attendance management"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'school') or not user.school:
            return Attendance.objects.none()
            
        queryset = Attendance.objects.filter(student__school=user.school)
        
        # Handle both term_id and term parameters
        term_id = self.request.query_params.get('term_id') or self.request.query_params.get('term')
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        
        # Handle both student_id and student parameters
        student_id = self.request.query_params.get('student_id') or self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_behaviour_record(request):
    """Simple function-based view to create behaviour records"""
    user = request.user
    
    if not hasattr(user, 'school') or not user.school:
        return Response({'error': 'User not attached to school'}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate student belongs to user's school
    student_id = request.data.get('student')
    if student_id:
        try:
            student = Student.objects.get(id=student_id, school=user.school)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = BehaviourSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BehaviourViewSet(viewsets.ModelViewSet):
    """Behaviour/Conduct management"""
    queryset = Behaviour.objects.all()
    serializer_class = BehaviourSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """Override list to provide better error handling"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'results': serializer.data,
                'count': len(serializer.data)
            })
        except Exception as e:
            # Return empty list instead of error for better UX
            return Response({
                'results': [],
                'count': 0,
                'message': 'No behavior records found'
            }, status=status.HTTP_200_OK)
    
    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'school') or not user.school:
            return Behaviour.objects.none()
            
        queryset = Behaviour.objects.filter(student__school=user.school)
        
        # Handle both term_id and term parameters
        term_id = self.request.query_params.get('term_id') or self.request.query_params.get('term')
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        
        # Handle both student_id and student parameters
        student_id = self.request.query_params.get('student_id') or self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset.select_related('student', 'term')
    
    def create(self, request, *args, **kwargs):
        """Override create method"""
        user = request.user
        
        if not hasattr(user, 'school') or not user.school:
            return Response({'error': 'User not attached to school'}, status=status.HTTP_403_FORBIDDEN)
        
        # Validate student belongs to user's school
        student_id = request.data.get('student')
        if student_id:
            try:
                student = Student.objects.get(id=student_id, school=user.school)
            except Student.DoesNotExist:
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Get dropdown choices for behaviour fields"""
        return Response({
            'conduct_choices': Behaviour.CONDUCT_CHOICES,
            'attitude_choices': Behaviour.ATTITUDE_CHOICES,
            'interest_choices': Behaviour.INTEREST_CHOICES,
            'teacher_remarks_templates': Behaviour.get_teacher_remarks_templates()
        })


class StudentPromotionViewSet(viewsets.ReadOnlyModelViewSet):
    """Student promotion history"""
    queryset = StudentPromotion.objects.all()
    serializer_class = StudentPromotionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'school') or not user.school:
            return StudentPromotion.objects.none()
        return StudentPromotion.objects.filter(student__school=user.school)
