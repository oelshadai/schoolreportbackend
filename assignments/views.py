from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from .models import Assignment, StudentAssignment, StudentPortalAccess, TimedTask, TaskAttempt, TaskAnswer, TaskQuestion, AssignmentAttempt
from .serializers import AssignmentSerializer, StudentAssignmentSerializer, StudentPortalAccessSerializer, AssignmentAttemptSerializer
from students.models import Student


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_assignment_history(request):
    """Get student's assignment history with all attempts"""
    try:
        student = Student.objects.get(user=request.user)
        
        # Get all student assignments that have been completed (graded)
        completed_assignments = StudentAssignment.objects.filter(
            student=student,
            status='GRADED'
        ).select_related('assignment').prefetch_related('attempts')
        
        history_data = []
        for student_assignment in completed_assignments:
            attempts_data = []
            for attempt in student_assignment.attempts.all():
                attempts_data.append({
                    'attempt_number': attempt.attempt_number,
                    'score': float(attempt.score) if attempt.score else 0,
                    'teacher_feedback': attempt.teacher_feedback,
                    'submitted_at': attempt.submitted_at,
                    'graded_at': attempt.graded_at,
                    'status': attempt.status
                })
            
            history_data.append({
                'id': student_assignment.assignment.id,
                'title': student_assignment.assignment.title,
                'subject': student_assignment.assignment.class_subject.subject.name if student_assignment.assignment.class_subject else 'General',
                'teacher': student_assignment.assignment.created_by.get_full_name() if student_assignment.assignment.created_by else 'Unknown',
                'assignment_type': student_assignment.assignment.get_assignment_type_display(),
                'due_date': student_assignment.assignment.due_date,
                'max_score': student_assignment.assignment.max_score,
                'final_score': float(student_assignment.score) if student_assignment.score else 0,
                'attempts_count': student_assignment.attempts_count,
                'max_attempts': student_assignment.max_attempts,
                'completed_at': student_assignment.graded_at,
                'attempts': attempts_data
            })
        
        return Response({
            'results': history_data,
            'count': len(history_data)
        })
        
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_assignment_attempt(request, assignment_id):
    """Start a new attempt at an assignment"""
    try:
        student = Student.objects.get(user=request.user)
        assignment = Assignment.objects.get(id=assignment_id, status='PUBLISHED')
        
        # Get or create student assignment
        student_assignment, created = StudentAssignment.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'status': 'NOT_STARTED'}
        )
        
        # Check if student can attempt
        if not student_assignment.can_attempt:
            return Response({
                'error': 'Maximum attempts reached',
                'attempts_used': student_assignment.attempts_count,
                'max_attempts': student_assignment.max_attempts
            }, status=400)
        
        # Check if assignment is still open
        if assignment.due_date < timezone.now():
            return Response({'error': 'Assignment deadline has passed'}, status=400)
        
        # Create new attempt
        attempt_number = student_assignment.attempts_count + 1
        attempt = AssignmentAttempt.objects.create(
            student_assignment=student_assignment,
            attempt_number=attempt_number,
            status='IN_PROGRESS'
        )
        
        # Update student assignment
        student_assignment.attempts_count = attempt_number
        student_assignment.status = 'IN_PROGRESS'
        student_assignment.save()
        
        return Response({
            'attempt_id': attempt.id,
            'attempt_number': attempt_number,
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'max_score': assignment.max_score,
                'due_date': assignment.due_date
            },
            'attempts_remaining': student_assignment.attempts_remaining
        })
        
    except (Student.DoesNotExist, Assignment.DoesNotExist):
        return Response({'error': 'Invalid request'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_assignment_attempt(request, attempt_id):
    """Submit an assignment attempt"""
    try:
        student = Student.objects.get(user=request.user)
        attempt = AssignmentAttempt.objects.get(
            id=attempt_id,
            student_assignment__student=student,
            status='IN_PROGRESS'
        )
        
        # Update attempt with submission
        attempt.submission_text = request.data.get('submission_text', '')
        attempt.status = 'SUBMITTED'
        attempt.submitted_at = timezone.now()
        
        # Handle file upload if present
        if 'submission_file' in request.FILES:
            attempt.submission_file = request.FILES['submission_file']
        
        attempt.save()
        
        # Update student assignment status
        student_assignment = attempt.student_assignment
        student_assignment.status = 'SUBMITTED'
        student_assignment.submitted_at = timezone.now()
        student_assignment.save()
        
        return Response({
            'status': 'Assignment attempt submitted successfully',
            'attempt_number': attempt.attempt_number,
            'submitted_at': attempt.submitted_at
        })
        
    except (Student.DoesNotExist, AssignmentAttempt.DoesNotExist):
        return Response({'error': 'Invalid request'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_student_assignments_with_attempts(request):
    """Get student's current assignments with attempt information"""
    try:
        student = Student.objects.get(user=request.user)
        
        # Get all published assignments for student's class
        student_assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        ).select_related('assignment').prefetch_related('attempts')
        
        assignments_data = []
        for student_assignment in student_assignments:
            assignment = student_assignment.assignment
            
            # Get latest attempt if any
            latest_attempt = student_assignment.attempts.first()  # ordered by -attempt_number
            
            assignments_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'subject': assignment.class_subject.subject.name if assignment.class_subject else 'General',
                'assignment_type': assignment.get_assignment_type_display(),
                'due_date': assignment.due_date,
                'max_score': assignment.max_score,
                'status': student_assignment.status,
                'attempts_count': student_assignment.attempts_count,
                'max_attempts': student_assignment.max_attempts,
                'can_attempt': student_assignment.can_attempt,
                'attempts_remaining': student_assignment.attempts_remaining,
                'is_overdue': student_assignment.is_overdue,
                'final_score': float(student_assignment.score) if student_assignment.score else None,
                'latest_attempt': {
                    'id': latest_attempt.id,
                    'attempt_number': latest_attempt.attempt_number,
                    'status': latest_attempt.status,
                    'score': float(latest_attempt.score) if latest_attempt.score else None,
                    'submitted_at': latest_attempt.submitted_at
                } if latest_attempt else None
            })
        
        return Response({
            'results': assignments_data,
            'count': len(assignments_data)
        })
        
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def test_endpoint(request):
    """Test endpoint to verify API is working"""
    return Response({
        'status': 'success',
        'message': 'Assignments API is working',
        'user_authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'timestamp': timezone.now()
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_timed_task(request):
    """Create a new timed task"""
    try:
        data = request.data
        
        # Create the task
        task = TimedTask.objects.create(
            title=data['title'],
            description=data.get('description', ''),
            class_instance_id=data['class_id'],
            created_by=request.user,
            start_time=data['start_time'],
            duration=data['duration'],
            status='SCHEDULED'
        )
        
        # Create questions
        for i, q_data in enumerate(data['questions']):
            TaskQuestion.objects.create(
                task=task,
                question_text=q_data['question'],
                option_a=q_data['options'][0],
                option_b=q_data['options'][1],
                option_c=q_data['options'][2],
                option_d=q_data['options'][3],
                correct_answer=q_data['correct_answer'],
                order=i
            )
        
        return Response({
            'id': task.id,
            'title': task.title,
            'status': 'Task created successfully'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def activate_task(request, task_id):
    """Activate a scheduled task"""
    try:
        task = TimedTask.objects.get(id=task_id, created_by=request.user)
        task.status = 'ACTIVE'
        task.save()
        
        return Response({'status': 'Task activated'})
    except TimedTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # Changed from AllowAny
def get_student_tasks(request):
    """Get available tasks for student"""
    try:
        # Get student profile
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({
                'error': 'Student profile not found',
                'detail': 'No student profile associated with this user account',
                'results': []
            }, status=404)
        
        # Check if student has a class assigned
        if not student.current_class:
            return Response({
                'error': 'No class assigned',
                'detail': 'Student is not assigned to any class',
                'results': []
            }, status=200)
        
        # Get active tasks for student's class
        now = timezone.now()
        tasks = TimedTask.objects.filter(
            class_instance=student.current_class,
            status='ACTIVE',
            start_time__lte=now
        )
        
        task_data = []
        for task in tasks:
            try:
                # Check if student already attempted
                attempt = TaskAttempt.objects.filter(task=task, student=student).first()
                
                end_time = task.start_time + timezone.timedelta(minutes=task.duration)
                is_available = now <= end_time and (not attempt or attempt.status == 'IN_PROGRESS')
                
                task_data.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'duration': task.duration,
                    'start_time': task.start_time,
                    'end_time': end_time,
                    'is_available': is_available,
                    'attempt_status': attempt.status if attempt else None,
                    'score': float(attempt.score) if attempt and attempt.score else None
                })
            except Exception as task_error:
                print(f"Error processing task {task.id}: {task_error}")
                continue
        
        return Response({
            'results': task_data,
            'count': len(task_data),
            'student_info': {
                'name': student.get_full_name(),
                'class': str(student.current_class) if student.current_class else None
            }
        })
        
    except Exception as e:
        print(f"Error in get_student_tasks: {e}")
        return Response({
            'error': 'Internal server error',
            'detail': str(e),
            'results': []
        }, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_task(request, task_id):
    """Start a task attempt"""
    try:
        student = Student.objects.get(user=request.user)
        task = TimedTask.objects.get(id=task_id)
        
        # Check if task is available
        if not task.can_start:
            return Response({'error': 'Task not available'}, status=400)
        
        # Check if already attempted
        existing_attempt = TaskAttempt.objects.filter(task=task, student=student).first()
        if existing_attempt:
            if existing_attempt.status != 'IN_PROGRESS':
                return Response({'error': 'Task already completed'}, status=400)
            attempt = existing_attempt
        else:
            attempt = TaskAttempt.objects.create(task=task, student=student)
        
        # Get questions
        questions = list(task.questions.all().values(
            'id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'order'
        ))
        
        # Format questions for frontend
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'id': q['id'],
                'question': q['question_text'],
                'options': [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
            })
        
        return Response({
            'attempt_id': attempt.id,
            'task': {
                'id': task.id,
                'title': task.title,
                'duration': task.duration,
                'questions': formatted_questions
            },
            'time_remaining': attempt.time_remaining
        })
        
    except (Student.DoesNotExist, TimedTask.DoesNotExist):
        return Response({'error': 'Invalid request'}, status=404)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_answer(request, attempt_id):
    """Submit answer for a question"""
    try:
        student = Student.objects.get(user=request.user)
        attempt = TaskAttempt.objects.get(id=attempt_id, student=student)
        
        if attempt.status != 'IN_PROGRESS':
            return Response({'error': 'Attempt not active'}, status=400)
        
        question_id = request.data['question_id']
        selected_option = request.data['selected_option']
        
        question = TaskQuestion.objects.get(id=question_id, task=attempt.task)
        
        # Save or update answer
        answer, created = TaskAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'selected_option': selected_option}
        )
        
        return Response({'status': 'Answer saved'})
        
    except (Student.DoesNotExist, TaskAttempt.DoesNotExist, TaskQuestion.DoesNotExist):
        return Response({'error': 'Invalid request'}, status=404)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_task(request, attempt_id):
    """Submit completed task"""
    try:
        student = Student.objects.get(user=request.user)
        attempt = TaskAttempt.objects.get(id=attempt_id, student=student)
        
        if attempt.status != 'IN_PROGRESS':
            return Response({'error': 'Attempt not active'}, status=400)
        
        # Calculate time taken
        time_taken = (timezone.now() - attempt.started_at).total_seconds()
        
        # Submit attempt
        attempt.status = 'SUBMITTED'
        attempt.submitted_at = timezone.now()
        attempt.time_taken = int(time_taken)
        attempt.calculate_score()
        
        return Response({
            'status': 'Task submitted successfully',
            'score': float(attempt.score),
            'time_taken': attempt.time_taken
        })
        
    except (Student.DoesNotExist, TaskAttempt.DoesNotExist):
        return Response({'error': 'Invalid request'}, status=404)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_task_results(request, task_id):
    """Get task results for teacher"""
    try:
        task = TimedTask.objects.get(id=task_id, created_by=request.user)
        attempts = TaskAttempt.objects.filter(task=task).select_related('student')
        
        results = []
        for attempt in attempts:
            results.append({
                'student_name': attempt.student.get_full_name(),
                'student_id': attempt.student.student_id,
                'status': attempt.status,
                'score': float(attempt.score) if attempt.score else 0,
                'time_taken': attempt.time_taken,
                'submitted_at': attempt.submitted_at
            })
        
        return Response({
            'task_title': task.title,
            'total_students': task.class_instance.students.count(),
            'attempts': len(results),
            'results': results
        })
        
    except TimedTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_assignments(request):
    """Debug endpoint to check assignments and student assignments"""
    try:
        # Get all assignments
        assignments = Assignment.objects.all().select_related('class_instance', 'created_by')
        
        # Get all student assignments
        student_assignments = StudentAssignment.objects.all().select_related('assignment', 'student')
        
        # Get current user's student profile if exists
        student_profile = None
        try:
            student_profile = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            pass
        
        debug_data = {
            'total_assignments': assignments.count(),
            'total_student_assignments': student_assignments.count(),
            'current_user': {
                'id': request.user.id,
                'email': request.user.email,
                'role': getattr(request.user, 'role', 'Unknown'),
                'student_profile': {
                    'id': student_profile.id if student_profile else None,
                    'name': student_profile.get_full_name() if student_profile else None,
                    'class': str(student_profile.current_class) if student_profile and student_profile.current_class else None
                } if student_profile else None
            },
            'assignments': [
                {
                    'id': assignment.id,
                    'title': assignment.title,
                    'status': assignment.status,
                    'class': str(assignment.class_instance),
                    'created_by': assignment.created_by.email if assignment.created_by else 'Unknown',
                    'student_assignments_count': StudentAssignment.objects.filter(assignment=assignment).count()
                }
                for assignment in assignments
            ],
            'student_assignments_for_current_user': [
                {
                    'id': sa.id,
                    'assignment_title': sa.assignment.title,
                    'assignment_status': sa.assignment.status,
                    'student_assignment_status': sa.status,
                    'student_name': sa.student.get_full_name()
                }
                for sa in student_assignments.filter(student=student_profile) if student_profile
            ] if student_profile else []
        }
        
        return Response(debug_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_assignment(request):
    """Simple assignment creation endpoint"""
    try:
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            # Set status to PUBLISHED so students can see it immediately
            assignment = serializer.save(created_by=request.user, status='PUBLISHED')
            
            # Create StudentAssignment records for all students in the class
            from students.models import Student
            students = Student.objects.filter(
                current_class=assignment.class_instance,
                is_active=True
            )
            
            print(f"Creating assignment '{assignment.title}' for class {assignment.class_instance}")
            print(f"Found {students.count()} students in class")
            
            created_count = 0
            for student in students:
                student_assignment, created = StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
                if created:
                    created_count += 1
                    print(f"Created assignment for student: {student.get_full_name()}")
            
            print(f"Created {created_count} student assignments")
            
            # Create notification for new assignment
            try:
                from notifications.models import Notification
                
                # Create notifications for all students in the class
                for student in students:
                    if student.user:  # Only create notification if student has a user account
                        Notification.objects.create(
                            user=student.user,
                            title=f'New {assignment.assignment_type.title()}: {assignment.title}',
                            message=f'A new {assignment.assignment_type.lower()} "{assignment.title}" has been assigned. Due: {assignment.due_date.strftime("%B %d, %Y at %I:%M %p")}',
                            type='info'
                        )
            except Exception as e:
                print(f'Failed to create notifications: {e}')
            
            return Response({
                **serializer.data,
                'students_assigned': created_count,
                'total_students': students.count()
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f'Assignment creation error: {e}')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignmentViewSet(viewsets.ModelViewSet):
    """Teacher assignment management"""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'user_type') and user.user_type == 'TEACHER':
            return Assignment.objects.filter(created_by=user)
        elif hasattr(user, 'role') and user.role == 'TEACHER':
            return Assignment.objects.filter(created_by=user)
        # Allow all authenticated users to create assignments for now
        return Assignment.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        # Always set status to PUBLISHED when creating through API
        assignment = serializer.save(created_by=self.request.user, status='PUBLISHED')
        
        # Create StudentAssignment records for all active students in the class
        from students.models import Student
        students = Student.objects.filter(
            current_class=assignment.class_instance,
            is_active=True
        )
        
        print(f"Creating assignment '{assignment.title}' for {students.count()} students in {assignment.class_instance}")
        
        created_count = 0
        for student in students:
            student_assignment, created = StudentAssignment.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )
            if created:
                created_count += 1
                print(f"✓ Created assignment for: {student.get_full_name()}")
        
        print(f"Successfully created {created_count} student assignments")
        
        # Create notifications for students
        try:
            from notifications.models import Notification
            for student in students:
                if student.user:
                    Notification.objects.create(
                        user=student.user,
                        title=f'New {assignment.get_assignment_type_display()}: {assignment.title}',
                        message=f'A new {assignment.get_assignment_type_display().lower()} "{assignment.title}" has been assigned to your class. Due: {assignment.due_date.strftime("%B %d, %Y at %I:%M %p")}',
                        type='assignment'
                    )
        except Exception as e:
            print(f'Warning: Could not create notifications: {e}')
    
    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):
        """Extend assignment due date"""
        assignment = self.get_object()
        new_due_date = request.data.get('due_date')
        
        if not new_due_date:
            return Response({'error': 'New due date is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            assignment.due_date = datetime.fromisoformat(new_due_date.replace('Z', '+00:00'))
            assignment.save()
            
            # Notify students about extension
            try:
                from notifications.models import Notification
                students = Student.objects.filter(current_class=assignment.class_instance, is_active=True)
                for student in students:
                    if student.user:
                        Notification.objects.create(
                            user=student.user,
                            title=f'Due Date Extended: {assignment.title}',
                            message=f'The due date for "{assignment.title}" has been extended to {assignment.due_date.strftime("%B %d, %Y at %I:%M %p")}',
                            type='info'
                        )
            except Exception as e:
                print(f'Failed to create extension notifications: {e}')
            
            return Response({'status': 'Due date extended successfully', 'new_due_date': assignment.due_date})
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def delete_assignment(self, request, pk=None):
        """Delete assignment and notify students"""
        assignment = self.get_object()
        assignment_title = assignment.title
        
        # Notify students about deletion
        try:
            from notifications.models import Notification
            students = Student.objects.filter(current_class=assignment.class_instance, is_active=True)
            for student in students:
                if student.user:
                    Notification.objects.create(
                        user=student.user,
                        title=f'Assignment Cancelled: {assignment_title}',
                        message=f'The assignment "{assignment_title}" has been cancelled by your teacher.',
                        type='warning'
                    )
        except Exception as e:
            print(f'Failed to create deletion notifications: {e}')
        
        assignment.delete()
        return Response({'status': 'Assignment deleted successfully'})
    
    @action(detail=False, methods=['get'])
    def class_review(self, request):
        """Get all assignments for teacher's classes with student progress"""
        user = request.user
        
        # Get classes where user is teacher
        from schools.models import Class, ClassSubject
        teacher_classes = Class.objects.filter(class_teacher=user)
        subject_classes = ClassSubject.objects.filter(teacher=user).values_list('class_instance', flat=True)
        all_class_ids = list(teacher_classes.values_list('id', flat=True)) + list(subject_classes)
        
        assignments = Assignment.objects.filter(
            class_instance_id__in=all_class_ids
        ).select_related('class_instance').prefetch_related('student_assignments__student')
        
        class_data = []
        for assignment in assignments:
            student_assignments = assignment.student_assignments.all()
            total_students = student_assignments.count()
            submitted = student_assignments.filter(status='SUBMITTED').count()
            graded = student_assignments.filter(status='GRADED').count()
            
            class_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'type': assignment.assignment_type,
                'class': str(assignment.class_instance),
                'due_date': assignment.due_date,
                'status': assignment.status,
                'progress': {
                    'total_students': total_students,
                    'submitted': submitted,
                    'graded': graded,
                    'pending': total_students - submitted
                }
            })
        
        return Response(class_data)
    
    @action(detail=False, methods=['post'])
    def create_announcement(self, request):
        """Create announcement for class"""
        title = request.data.get('title')
        message = request.data.get('message')
        class_id = request.data.get('class_id')
        
        if not all([title, message, class_id]):
            return Response({'error': 'Title, message, and class_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from schools.models import Class
            class_instance = Class.objects.get(id=class_id)
            students = Student.objects.filter(current_class=class_instance, is_active=True)
            
            # Create notifications for all students in class
            from notifications.models import Notification
            created_count = 0
            for student in students:
                if student.user:
                    Notification.objects.create(
                        user=student.user,
                        title=f'Announcement: {title}',
                        message=message,
                        type='info'
                    )
                    created_count += 1
            
            return Response({
                'status': 'Announcement sent successfully',
                'students_notified': created_count
            })
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish assignment to students"""
        assignment = self.get_object()
        assignment.status = 'PUBLISHED'
        assignment.save()
        
        # Create StudentAssignment records for all students in the class
        students = Student.objects.filter(current_class=assignment.class_instance)
        for student in students:
            StudentAssignment.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )
        
        # Create notifications for students
        try:
            from notifications.models import Notification
            for student in students:
                if student.user:
                    Notification.objects.create(
                        user=student.user,
                        title=f'New {assignment.assignment_type.title()}: {assignment.title}',
                        message=f'A new {assignment.assignment_type.lower()} "{assignment.title}" has been assigned. Due: {assignment.due_date.strftime("%B %d, %Y at %I:%M %p")}',
                        type='info'
                    )
        except Exception as e:
            print(f'Failed to create notifications: {e}')
        
        return Response({'status': 'Assignment published successfully'})
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Get all student submissions for this assignment"""
        assignment = self.get_object()
        submissions = StudentAssignment.objects.filter(assignment=assignment)
        serializer = StudentAssignmentSerializer(submissions, many=True)
        return Response(serializer.data)


class StudentAssignmentViewSet(viewsets.ModelViewSet):
    """Student assignment submissions and grading"""
    serializer_class = StudentAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'user_type') and user.user_type == 'TEACHER':
            # Teachers can see all submissions for their assignments
            return StudentAssignment.objects.filter(assignment__created_by=user)
        elif hasattr(user, 'role') and user.role == 'TEACHER':
            return StudentAssignment.objects.filter(assignment__created_by=user)
        # Allow all authenticated users for now
        return StudentAssignment.objects.filter(assignment__created_by=user)
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """Grade a student submission"""
        submission = self.get_object()
        score = request.data.get('score')
        feedback = request.data.get('teacher_feedback', '')
        
        if score is not None:
            submission.score = score
            submission.teacher_feedback = feedback
            submission.status = 'GRADED'
            submission.graded_at = timezone.now()
            submission.save()
            
            return Response({'status': 'Submission graded successfully'})
        
        return Response({'error': 'Score is required'}, status=status.HTTP_400_BAD_REQUEST)


class StudentPortalViewSet(viewsets.ModelViewSet):
    """Student portal access management"""
    serializer_class = StudentPortalAccessSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'user_type') and user.user_type == 'TEACHER':
            # Teachers can manage portal access for students in their school
            return StudentPortalAccess.objects.filter(student__school=user.school)
        elif hasattr(user, 'role') and user.role == 'TEACHER':
            return StudentPortalAccess.objects.filter(student__school=user.school)
        # Allow all authenticated users for now
        return StudentPortalAccess.objects.all()
    
    def perform_create(self, serializer):
        # Hash the password before saving
        password = self.request.data.get('password')
        if password:
            serializer.save(password_hash=make_password(password))
    
    @action(detail=False, methods=['post'])
    def student_login(self, request):
        """Student portal login"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            portal_access = StudentPortalAccess.objects.get(username=username, is_active=True)
            if check_password(password, portal_access.password_hash):
                portal_access.last_login = timezone.now()
                portal_access.save()
                
                # Return student info and assignments
                student = portal_access.student
                assignments = StudentAssignment.objects.filter(
                    student=student,
                    assignment__status='PUBLISHED'
                ).select_related('assignment')
                
                return Response({
                    'student': {
                        'id': student.id,
                        'name': student.get_full_name(),
                        'student_id': student.student_id,
                        'class': student.current_class.full_name if student.current_class else None
                    },
                    'assignments': StudentAssignmentSerializer(assignments, many=True).data
                })
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except StudentPortalAccess.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'])
    def submit_assignment(self, request):
        """Student assignment submission"""
        assignment_id = request.data.get('assignment_id')
        student_username = request.data.get('username')
        submission_text = request.data.get('submission_text', '')
        
        try:
            portal_access = StudentPortalAccess.objects.get(username=student_username, is_active=True)
            student_assignment = StudentAssignment.objects.get(
                assignment_id=assignment_id,
                student=portal_access.student
            )
            
            # Check if assignment is still open
            if student_assignment.assignment.due_date < timezone.now():
                return Response({'error': 'Assignment deadline has passed'}, status=status.HTTP_400_BAD_REQUEST)
            
            student_assignment.submission_text = submission_text
            student_assignment.status = 'SUBMITTED'
            student_assignment.submitted_at = timezone.now()
            
            # Handle file upload if present
            if 'submission_file' in request.FILES:
                student_assignment.submission_file = request.FILES['submission_file']
            
            student_assignment.save()
            
            return Response({'status': 'Assignment submitted successfully'})
            
        except (StudentPortalAccess.DoesNotExist, StudentAssignment.DoesNotExist):
            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def student_reports(self, request):
        """Get student reports and grades"""
        username = request.query_params.get('username')
        
        if not username:
            return Response({'error': 'Username required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            portal_access = StudentPortalAccess.objects.get(username=username, is_active=True)
            student = portal_access.student
            
            # Get graded assignments
            graded_assignments = StudentAssignment.objects.filter(
                student=student,
                status='GRADED'
            ).select_related('assignment')
            
            # Get student scores from the scores app
            from scores.models import Score
            scores = Score.objects.filter(student=student).select_related('subject', 'exam')
            
            return Response({
                'student': {
                    'name': student.get_full_name(),
                    'student_id': student.student_id,
                    'class': student.current_class.full_name if student.current_class else None
                },
                'assignments': StudentAssignmentSerializer(graded_assignments, many=True).data,
                'exam_scores': [
                    {
                        'subject': score.subject.name,
                        'exam': score.exam.name,
                        'score': score.score,
                        'total': score.exam.total_marks,
                        'percentage': (score.score / score.exam.total_marks * 100) if score.exam.total_marks > 0 else 0
                    }
                    for score in scores
                ]
            })
            
        except StudentPortalAccess.DoesNotExist:
            return Response({'error': 'Invalid username'}, status=status.HTTP_400_BAD_REQUEST)