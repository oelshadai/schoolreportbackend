from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from datetime import date
from students.models import DailyAttendance, Student
from schools.models import Class

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_attendance_my_classes(request):
    """Get classes assigned to current teacher"""
    try:
        classes = Class.objects.filter(
            class_teacher=request.user,
            school=request.user.school
        )
        
        classes_data = []
        for cls in classes:
            student_count = Student.objects.filter(
                current_class=cls,
                is_active=True
            ).count()
            
            # Check if attendance taken today
            today = date.today()
            attendance_taken_today = DailyAttendance.objects.filter(
                class_instance=cls,
                date=today,
                marked_by=request.user
            ).exists()
            
            classes_data.append({
                'id': cls.id,
                'name': str(cls),
                'level': cls.get_level_display(),
                'student_count': student_count,
                'attendance_taken_today': attendance_taken_today
            })
        
        return Response({'classes': classes_data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_attendance_class_students(request):
    """Get students in a class for attendance taking"""
    class_id = request.query_params.get('class_id')
    date_str = request.query_params.get('date', str(date.today()))
    selected_date = parse_date(date_str) or date.today()
    
    if not class_id:
        return Response({'error': 'class_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        cls = Class.objects.get(
            id=class_id,
            class_teacher=request.user,
            school=request.user.school
        )
    except Class.DoesNotExist:
        return Response({'error': 'Class not found or not assigned to you'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all active students in the class
    students = Student.objects.filter(
        current_class=cls,
        is_active=True
    ).order_by('last_name', 'first_name')
    
    # Get existing attendance records for the date
    existing_attendance = DailyAttendance.objects.filter(
        class_instance=cls,
        date=selected_date
    ).select_related('student')
    
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
    
    return Response({
        'class': {
            'id': cls.id,
            'name': str(cls),
            'level': cls.get_level_display()
        },
        'date': selected_date.isoformat(),
        'students': students_data,
        'attendance_already_taken': len(attendance_map) > 0
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_attendance_save(request):
    """Save attendance for a class"""
    class_id = request.data.get('class_id')
    date_str = request.data.get('date', str(date.today()))
    attendance_data = request.data.get('attendance', [])
    
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
    except Class.DoesNotExist:
        return Response({
            'error': 'Class not found or not assigned to you'
        }, status=status.HTTP_404_NOT_FOUND)
    
    saved_count = 0
    updated_count = 0
    errors = []
    
    for item in attendance_data:
        student_id = item.get('student_id')
        status_value = item.get('status', 'absent')
        
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
            
            if created:
                saved_count += 1
            else:
                updated_count += 1
                
        except Student.DoesNotExist:
            errors.append(f'Student with ID {student_id} not found in class')
            continue
        except Exception as e:
            errors.append(f'Error saving attendance for student {student_id}: {str(e)}')
            continue
    
    return Response({
        'message': 'Attendance saved successfully',
        'saved_count': saved_count,
        'updated_count': updated_count,
        'total_processed': saved_count + updated_count,
        'errors': errors
    })