from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from datetime import date, datetime
from students.models import DailyAttendance, Student
from schools.models import Class

class TeacherAttendanceViewSet(viewsets.ViewSet):
    """Teacher attendance management - for teachers to take and manage attendance"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List endpoint - redirect to my_classes"""
        print(f"DEBUG: TeacherAttendanceViewSet.list called by {request.user.email}")
        return self.my_classes(request)
    
    def get_teacher_classes(self):
        """Get classes assigned to the current teacher"""
        return Class.objects.filter(
            class_teacher=self.request.user,
            school=self.request.user.school
        )
    
    @action(detail=False, methods=['get'], url_path='my-classes')
    def my_classes(self, request):
        """Get classes assigned to current teacher"""
        print(f"DEBUG: my_classes action called by {request.user.email}")
        
        # Simple test response
        return Response({
            'classes': [{
                'id': 1,
                'name': 'Test Class',
                'level': 'Basic 1',
                'student_count': 0,
                'attendance_taken_today': False
            }],
            'message': 'Test response from ViewSet'
        })
    
    @action(detail=False, methods=['get'], url_path='class-students')
    def class_students(self, request):
        """Get students in a specific class for attendance taking"""
        class_id = request.query_params.get('class_id')
        date_str = request.query_params.get('date', str(date.today()))
        selected_date = parse_date(date_str) or date.today()
        
        print(f"DEBUG: Getting class students - class_id: {class_id}, date: {date_str}")
        
        if not class_id:
            return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cls = Class.objects.get(
                id=class_id,
                class_teacher=request.user,
                school=request.user.school
            )
            print(f"DEBUG: Found class: {cls}")
        except Class.DoesNotExist:
            return Response({'error': 'Class not found or not assigned to you'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all active students in the class
        students = Student.objects.filter(
            current_class=cls,
            is_active=True
        ).order_by('last_name', 'first_name')
        
        print(f"DEBUG: Found {students.count()} students in class")
        
        # Get existing attendance records for the date
        existing_attendance = DailyAttendance.objects.filter(
            class_instance=cls,
            date=selected_date
        ).select_related('student')
        
        print(f"DEBUG: Found {existing_attendance.count()} existing attendance records for {selected_date}")
        
        # Create a mapping of student_id to attendance status
        attendance_map = {att.student_id: att.status for att in existing_attendance}
        
        students_data = []
        for student in students:
            current_status = attendance_map.get(student.id, 'absent')
            students_data.append({
                'id': student.id,
                'student_id': student.student_id,
                'name': student.get_full_name(),
                'photo': student.photo.url if student.photo else None,
                'current_status': current_status
            })
            print(f"DEBUG: Student {student.get_full_name()} - current status: {current_status}")
        
        response_data = {
            'class': {
                'id': cls.id,
                'name': str(cls),  # Use __str__ method instead of .name
                'level': cls.get_level_display()
            },
            'date': selected_date.isoformat(),
            'students': students_data,
            'attendance_already_taken': len(attendance_map) > 0
        }
        
        print(f"DEBUG: Returning response with {len(students_data)} students, attendance_already_taken: {len(attendance_map) > 0}")
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'], url_path='save-attendance')
    def save_attendance(self, request):
        """Save attendance for a class on a specific date"""
        class_id = request.data.get('class_id')
        date_str = request.data.get('date', str(date.today()))
        attendance_data = request.data.get('attendance', [])
        
        print(f"DEBUG: Saving attendance - class_id: {class_id}, date: {date_str}, attendance_data: {attendance_data}")
        
        if not class_id or not attendance_data:
            return Response({
                'error': 'class_id and attendance data are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        selected_date = parse_date(date_str) or date.today()
        
        try:
            cls = Class.objects.get(
                id=class_id,
                class_teacher=request.user,
                school=request.user.school
            )
            print(f"DEBUG: Found class: {cls}")
        except Class.DoesNotExist:
            return Response({
                'error': 'Class not found or not assigned to you'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate attendance data format
        if not isinstance(attendance_data, list):
            return Response({
                'error': 'Attendance data must be a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        for item in attendance_data:
            student_id = item.get('student_id')
            status_value = item.get('status', 'absent')
            
            print(f"DEBUG: Processing student_id: {student_id}, status: {status_value}")
            
            if not student_id:
                errors.append('Missing student_id in attendance data')
                continue
            
            try:
                student = Student.objects.get(
                    id=student_id,
                    current_class=cls,
                    is_active=True
                )
                
                # Create or update attendance record
                attendance, created = DailyAttendance.objects.update_or_create(
                    student=student,
                    class_instance=cls,
                    date=selected_date,
                    defaults={
                        'status': status_value,
                        'marked_by': request.user
                    }
                )
                
                print(f"DEBUG: {'Created' if created else 'Updated'} attendance for {student.get_full_name()}: {status_value}")
                
                if created:
                    saved_count += 1
                else:
                    updated_count += 1
                    
            except Student.DoesNotExist:
                errors.append(f'Student with ID {student_id} not found in class')
                continue
            except Exception as e:
                print(f"DEBUG: Error saving attendance for student {student_id}: {str(e)}")
                errors.append(f'Error saving attendance for student {student_id}: {str(e)}')
                continue
        
        print(f"DEBUG: Attendance save complete - saved: {saved_count}, updated: {updated_count}, errors: {len(errors)}")
        
        return Response({
            'message': 'Attendance saved successfully',
            'saved_count': saved_count,
            'updated_count': updated_count,
            'total_processed': saved_count + updated_count,
            'errors': errors
        })
    
    @action(detail=False, methods=['get'], url_path='attendance-history')
    def attendance_history(self, request):
        """Get attendance history for teacher's classes"""
        class_id = request.query_params.get('class_id')
        days = int(request.query_params.get('days', 7))  # Last 7 days by default
        
        if not class_id:
            return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cls = Class.objects.get(
                id=class_id,
                class_teacher=request.user,
                school=request.user.school
            )
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get attendance records for the last N days
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days-1)
        
        records = DailyAttendance.objects.filter(
            class_instance=cls,
            date__gte=start_date
        ).select_related('student').order_by('-date', 'student__last_name')
        
        # Group by date
        history_by_date = {}
        for record in records:
            date_key = record.date.isoformat()
            if date_key not in history_by_date:
                history_by_date[date_key] = []
            
            history_by_date[date_key].append({
                'student_name': record.student.get_full_name(),
                'student_id': record.student.student_id,
                'status': record.status
            })
        
        return Response({
            'class': {
                'id': cls.id,
                'name': str(cls)  # Use __str__ method instead of .name
            },
            'history': history_by_date
        })

class StudentAttendanceViewSet(viewsets.ViewSet):
    """Student attendance views - for students to view their own attendance"""
    permission_classes = [IsAuthenticated]

    def get_student(self):
        try:
            return Student.objects.get(user=self.request.user)
        except Student.DoesNotExist:
            return None

    def list(self, request):
        """GET /api/students/my-attendance/ — records + summary in one call"""
        student = self.get_student()
        if not student:
            return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)

        from datetime import timedelta
        start_date = date.today() - timedelta(days=90)

        records_qs = DailyAttendance.objects.filter(
            student=student,
            date__gte=start_date
        ).select_related('marked_by').order_by('-date')

        records = []
        for a in records_qs:
            records.append({
                'id': a.id,
                'date': a.date.isoformat(),
                'status': a.status,
                'reason': getattr(a, 'reason', '') or '',
                'marked_by': a.marked_by.get_full_name() if a.marked_by else 'Class Teacher',
            })

        total = records_qs.count()
        present = records_qs.filter(status='present').count()
        absent = records_qs.filter(status='absent').count()
        late = records_qs.filter(status='late').count()
        rate = round((present / total * 100), 1) if total > 0 else 0.0

        return Response({
            'records': records,
            'summary': {
                'present': present,
                'absent': absent,
                'late': late,
                'total': total,
                'rate': rate,
            }
        })

    @action(detail=False, methods=['post'], url_path='send-reason')
    def send_reason(self, request):
        """Student sends absence reason to class teacher"""
        student = self.get_student()
        if not student:
            return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)

        absence_date = request.data.get('date')
        reason = (request.data.get('reason') or '').strip()

        if not absence_date or not reason:
            return Response({'error': 'date and reason are required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(reason) > 500:
            return Response({'error': 'Reason must be under 500 characters'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the attendance record
        try:
            record = DailyAttendance.objects.get(student=student, date=absence_date)
        except DailyAttendance.DoesNotExist:
            return Response({'error': 'No attendance record found for that date'}, status=status.HTTP_404_NOT_FOUND)

        if record.status not in ('absent', 'late'):
            return Response({'error': 'You can only send a reason for absent or late records'}, status=status.HTTP_400_BAD_REQUEST)

        # Save reason on the record
        if hasattr(record, 'reason'):
            record.reason = reason
            record.save(update_fields=['reason'])

        # Notify class teacher via Notification model
        try:
            from notifications.models import Notification
            teacher = student.current_class.class_teacher if student.current_class else None
            if teacher:
                Notification.objects.create(
                    user=teacher,
                    title=f'Absence Reason: {student.get_full_name()}',
                    message=f'{student.get_full_name()} ({student.student_id}) was {record.status} on {absence_date}.\nReason: {reason}',
                    type='info',
                )
        except Exception as e:
            print(f'Failed to notify teacher: {e}')

        return Response({'message': 'Reason sent to your class teacher successfully'})

class AttendanceAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DailyAttendance.objects.filter(
            student__school=self.request.user.school
        )
    
    @action(detail=False, methods=['get'])
    def daily_stats(self, request):
        """Get daily attendance statistics"""
        date_str = request.query_params.get('date', str(date.today()))
        selected_date = parse_date(date_str) or date.today()
        
        # Get all students in the school
        total_students = Student.objects.filter(
            school=request.user.school,
            is_active=True
        ).count()
        
        # Get attendance records for the date
        attendance_records = self.get_queryset().filter(date=selected_date)
        
        present = attendance_records.filter(status='present').count()
        absent = attendance_records.filter(status='absent').count()
        late = attendance_records.filter(status='late').count()
        
        # Calculate attendance rate
        total_marked = present + absent + late
        attendance_rate = (present / total_marked * 100) if total_marked > 0 else 0
        
        stats = {
            'date': selected_date.isoformat(),
            'total_students': total_students,
            'present': present,
            'absent': absent,
            'late': late,
            'attendance_rate': round(attendance_rate, 1)
        }
        
        return Response({'stats': stats})
    
    @action(detail=False, methods=['get'])
    def class_summary(self, request):
        """Get attendance summary by class"""
        date_str = request.query_params.get('date', str(date.today()))
        selected_date = parse_date(date_str) or date.today()
        
        classes = Class.objects.filter(school=request.user.school)
        summaries = []
        
        for cls in classes:
            # Get all students in this class
            total_students = Student.objects.filter(
                current_class=cls,
                is_active=True
            ).count()
            
            if total_students == 0:
                continue
            
            # Get attendance records for this class on the date
            attendance_records = self.get_queryset().filter(
                date=selected_date,
                class_instance=cls
            )
            
            present = attendance_records.filter(status='present').count()
            absent = attendance_records.filter(status='absent').count()
            late = attendance_records.filter(status='late').count()
            
            # Calculate attendance rate
            total_marked = present + absent + late
            attendance_rate = (present / total_marked * 100) if total_marked > 0 else 0
            
            summaries.append({
                'class_name': str(cls),  # Use __str__ method instead of .name
                'class_id': cls.id,
                'total_students': total_students,
                'present': present,
                'absent': absent,
                'late': late,
                'attendance_rate': round(attendance_rate, 1)
            })
        
        return Response({'summaries': summaries})
    
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Get daily attendance records with filters"""
        date_str = request.query_params.get('date', str(date.today()))
        class_id = request.query_params.get('class')
        selected_date = parse_date(date_str) or date.today()
        
        queryset = self.get_queryset().filter(date=selected_date)
        
        # Filter by class if specified
        if class_id and class_id != 'all':
            queryset = queryset.filter(class_instance_id=class_id)
        
        records = []
        for attendance in queryset.select_related('student', 'class_instance', 'marked_by'):
            records.append({
                'id': attendance.id,
                'student_name': attendance.student.get_full_name(),
                'student_id': attendance.student.student_id,
                'class_name': str(attendance.class_instance),  # Use __str__ method
                'date': attendance.date.isoformat(),
                'status': attendance.status,
                'marked_by': attendance.marked_by.get_full_name() if attendance.marked_by else 'System'
            })
        
        return Response({'records': records})
    
    @action(detail=False, methods=['get'])
    def student_history(self, request):
        """Get attendance history for a specific student"""
        student_id = request.query_params.get('student_id')
        days = int(request.query_params.get('days', 30))
        
        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            student = Student.objects.get(
                student_id=student_id,
                school=request.user.school
            )
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get recent attendance records
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days)
        
        records = self.get_queryset().filter(
            student=student,
            date__gte=start_date
        ).order_by('-date')
        
        history = []
        for attendance in records:
            history.append({
                'date': attendance.date.isoformat(),
                'status': attendance.status,
                'class_name': str(attendance.class_instance),  # Use __str__ method
                'marked_by': attendance.marked_by.get_full_name() if attendance.marked_by else 'System'
            })
        
        # Calculate summary stats
        total_days = records.count()
        present_days = records.filter(status='present').count()
        absent_days = records.filter(status='absent').count()
        late_days = records.filter(status='late').count()
        
        attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
        
        return Response({
            'student': {
                'name': student.get_full_name(),
                'student_id': student.student_id,
                'class': student.current_class.full_name if student.current_class else None
            },
            'summary': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'attendance_rate': round(attendance_rate, 1)
            },
            'history': history
        })