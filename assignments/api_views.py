"""
Clean Assignment Management API
Professional implementation with proper separation of concerns
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction, models

from schools.models import Class, Term
from students.models import Student
from .models import Assignment, StudentAssignment, Question, QuestionOption, QuizAttempt, QuizAnswer
from .serializers import AssignmentSerializer, StudentAssignmentSerializer


class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    """Clean API for teachers to manage assignments"""
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentSerializer
    
    def get_queryset(self):
        """Get assignments for the current teacher"""
        user = self.request.user
        
        # Get all assignments where teacher has access
        from schools.models import ClassSubject
        
        teacher_subjects = ClassSubject.objects.filter(
            teacher=user
        ).values_list('id', flat=True)
        
        teacher_email = user.email
        
        # Get teacher's assignments
        return Assignment.objects.filter(
            models.Q(created_by=user) |
            models.Q(created_by__email=teacher_email) |
            models.Q(class_subject__in=teacher_subjects) |
            models.Q(class_instance__class_teacher=user) |
            models.Q(class_instance__class_teacher__email=teacher_email)
        ).distinct().select_related('class_instance').order_by('-created_at')
    
    def list(self, request):
        """List all assignments for teacher - FRONTEND COMPATIBILITY"""
        queryset = self.get_queryset()
        
        assignment_data = []
        for assignment in queryset:
            assignment_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'assignment_type': assignment.assignment_type,
                'due_date': assignment.due_date,
                'status': assignment.status,
                'max_score': assignment.max_score,
                'class_name': str(assignment.class_instance) if assignment.class_instance else 'No Class',
                'created_at': assignment.created_at,
                'updated_at': assignment.updated_at
            })
        
        return Response({
            'results': assignment_data,
            'count': len(assignment_data)
        })
    
    def retrieve(self, request, pk=None):
        """Get individual assignment details"""
        try:
            assignment = self.get_queryset().get(id=pk)
            
            assignment_data = {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'instructions': getattr(assignment, 'instructions', ''),
                'assignment_type': assignment.assignment_type,
                'due_date': assignment.due_date,
                'status': assignment.status,
                'max_score': assignment.max_score,
                'time_limit': getattr(assignment, 'time_limit', None),
                'max_attempts': getattr(assignment, 'max_attempts', 1),
                'class_instance': assignment.class_instance.id if assignment.class_instance else None,
                'class_name': str(assignment.class_instance) if assignment.class_instance else 'No Class',
                'created_at': assignment.created_at,
                'updated_at': assignment.updated_at
            }
            
            return Response(assignment_data)
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    def update(self, request, pk=None, **kwargs):
        """Update assignment details"""
        try:
            assignment = self.get_queryset().get(id=pk)
            
            data = request.data
            
            # Update fields without triggering full_clean validation
            assignment.title = data.get('title', assignment.title)
            assignment.description = data.get('description', assignment.description)
            if hasattr(assignment, 'instructions'):
                assignment.instructions = data.get('instructions', getattr(assignment, 'instructions', ''))
            assignment.due_date = data.get('due_date', assignment.due_date)
            assignment.max_score = data.get('max_score', assignment.max_score)
            if hasattr(assignment, 'time_limit'):
                assignment.time_limit = data.get('time_limit', getattr(assignment, 'time_limit', None))
            if hasattr(assignment, 'max_attempts'):
                assignment.max_attempts = data.get('max_attempts', getattr(assignment, 'max_attempts', 1))
            
            # Save without calling full_clean to avoid validation errors on draft assignments
            assignment.save(update_fields=[
                'title', 'description', 'instructions', 'due_date', 
                'max_score', 'time_limit', 'max_attempts', 'updated_at'
            ])
            
            return Response({
                'message': 'Assignment updated successfully',
                'id': assignment.id
            })
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            import traceback
            print(f"Error updating assignment: {e}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=400)
    
    def destroy(self, request, pk=None):
        """Delete assignment"""
        try:
            assignment = self.get_queryset().get(id=pk)
            assignment.delete()
            
            return Response({
                'message': 'Assignment deleted successfully'
            })
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    def create(self, request):
        """Create new assignment - FRONTEND COMPATIBILITY"""
        data = request.data
        
        # Handle both form data and JSON
        if hasattr(request, 'FILES'):
            # Handle multipart form data
            assignment_data = {
                'title': data.get('title'),
                'description': data.get('description'),
                'assignment_type': data.get('assignment_type', 'HOMEWORK'),
                'class_instance_id': data.get('class_instance'),
                'due_date': data.get('due_date'),
                'max_score': int(data.get('max_score', 10)),
                'created_by': request.user,
                'status': 'PUBLISHED'  # Auto-publish for now
            }
            
            # Handle attachment
            if 'attachment' in request.FILES:
                assignment_data['attachment'] = request.FILES['attachment']
        else:
            # Handle JSON data
            assignment_data = {
                'title': data['title'],
                'description': data['description'],
                'assignment_type': data.get('assignment_type', 'HOMEWORK'),
                'class_instance_id': data['class_instance'],
                'due_date': data['due_date'],
                'max_score': int(data.get('max_score', 10)),
                'created_by': request.user,
                'status': 'PUBLISHED'
            }
        
        try:
            with transaction.atomic():
                # Create assignment
                assignment = Assignment.objects.create(**assignment_data)
                
                # Auto-assign to all students in the class
                if assignment.class_instance:
                    students = assignment.class_instance.students.all()
                    for student in students:
                        StudentAssignment.objects.get_or_create(
                            assignment=assignment,
                            student=student,
                            defaults={'status': 'NOT_STARTED'}
                        )
                
                # Notify admins about assignment creation
                try:
                    from notifications.views import notify_admins_assignment_created
                    notify_admins_assignment_created(
                        school=request.user.school,
                        teacher=request.user,
                        assignment=assignment,
                        class_obj=assignment.class_instance
                    )
                except Exception as e:
                    print(f"Failed to notify admins about assignment: {e}")
                
                return Response({
                    'id': assignment.id,
                    'title': assignment.title,
                    'message': 'Assignment created successfully'
                }, status=201)
                
        except Exception as e:
            return Response({
                'error': f'Failed to create assignment: {str(e)}'
            }, status=400)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish assignment - FRONTEND COMPATIBILITY"""
        try:
            assignment = Assignment.objects.get(
                id=pk,
                created_by=request.user
            )
            
            assignment.status = 'PUBLISHED'
            assignment.published_at = timezone.now()
            assignment.save()
            
            # Auto-assign to all students in the class
            if assignment.class_instance:
                students = assignment.class_instance.students.all()
                for student in students:
                    StudentAssignment.objects.get_or_create(
                        assignment=assignment,
                        student=student,
                        defaults={'status': 'NOT_STARTED'}
                    )
            
            return Response({
                'message': 'Assignment published successfully',
                'status': assignment.status
            })
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get teacher's assignment dashboard"""
        class_id = request.query_params.get('class_id')
        if not class_id:
            return Response({'error': 'class_id required'}, status=400)
        
        try:
            class_instance = Class.objects.get(id=class_id)
            
            # Verify teacher has access to this class
            user = request.user
            has_access = (
                class_instance.class_teacher == user or
                class_instance.assigned_subjects.filter(teacher=user).exists()
            )
            
            if not has_access:
                return Response({'error': 'Access denied to this class'}, status=403)
                
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=404)
        
        # Get assignments for this class where teacher has access
        # Include assignments created by this user OR where user teaches the subject
        from schools.models import ClassSubject
        
        # Get all assignments for this class that the teacher can access
        teacher_subjects = ClassSubject.objects.filter(
            class_instance=class_instance,
            teacher=user
        ).values_list('id', flat=True)
        
        # Get teacher's email to match assignments created by same teacher account
        teacher_email = user.email
        
        # More comprehensive assignment filtering - include assignments by email match
        assignments = Assignment.objects.filter(
            class_instance=class_instance
        ).filter(
            # Either created by this teacher (by user ID or email) OR for a subject they teach
            models.Q(created_by=user) |
            models.Q(created_by__email=teacher_email) |
            models.Q(class_subject__in=teacher_subjects) |
            # Also include assignments where teacher is class teacher
            models.Q(class_instance__class_teacher=user) |
            models.Q(class_instance__class_teacher__email=teacher_email)
        ).distinct().order_by('-created_at')[:10]
        
        assignment_data = []
        for assignment in assignments:
            total_students = class_instance.students.count()
            submitted = StudentAssignment.objects.filter(
                assignment=assignment,
                status__in=['SUBMITTED', 'GRADED']
            ).count()
            
            assignment_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'type': assignment.assignment_type,
                'due_date': assignment.due_date,
                'status': assignment.status,
                'created_at': assignment.created_at,
                'max_score': assignment.max_score,
                'stats': {
                    'total_students': total_students,
                    'submitted': submitted,
                    'pending': total_students - submitted
                }
            })
        
        return Response({
            'class': {
                'id': class_instance.id,
                'name': str(class_instance),
                'student_count': class_instance.students.count()
            },
            'assignments': assignment_data
        })
    
    @action(detail=False, methods=['get'])
    def teacher_stats(self, request):
        """Get teacher's overall assignment statistics"""
        user = request.user
        
        # Get all assignments where teacher has access (created by them OR for subjects they teach)
        from schools.models import ClassSubject
        
        teacher_subjects = ClassSubject.objects.filter(
            teacher=user
        ).values_list('id', flat=True)
        
        # Get teacher's email to match assignments across sessions
        teacher_email = user.email
        
        # More comprehensive teacher assignment filtering - include assignments by email match
        teacher_assignments = Assignment.objects.filter(
            models.Q(created_by=user) |
            models.Q(created_by__email=teacher_email) |
            models.Q(class_subject__in=teacher_subjects) |
            # Include assignments where teacher is class teacher
            models.Q(class_instance__class_teacher=user) |
            models.Q(class_instance__class_teacher__email=teacher_email)
        ).distinct()
        
        return Response({
            'totalAssignments': teacher_assignments.count(),
            'assignmentStats': {
                'total': teacher_assignments.count(),
                'published': teacher_assignments.filter(status='PUBLISHED').count(),
                'draft': teacher_assignments.filter(status='DRAFT').count(),
                'closed': teacher_assignments.filter(status='CLOSED').count()
            }
        })
    
    @action(detail=False, methods=['post'])
    def create_assignment(self, request):
        """Create new assignment with questions"""
        data = request.data
        
        with transaction.atomic():
            # Create assignment
            assignment = Assignment.objects.create(
                title=data['title'],
                description=data['description'],
                assignment_type=data['assignment_type'],
                class_instance_id=data['class_instance'],
                created_by=request.user,
                due_date=data['due_date'],
                time_limit=data.get('time_limit'),
                max_score=data.get('max_score', 10),
                status='PUBLISHED'
            )
            
            # Create questions
            for q_data in data.get('questions', []):
                question = Question.objects.create(
                    assignment=assignment,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    points=q_data.get('points', 1),
                    order=q_data.get('order', 0)
                )
                
                # Create MCQ options
                if q_data['question_type'] == 'mcq':
                    for opt_data in q_data.get('options', []):
                        QuestionOption.objects.create(
                            question=question,
                            option_text=opt_data['option_text'],
                            is_correct=opt_data['is_correct'],
                            order=opt_data.get('order', 0)
                        )
            
            # Auto-assign to all students
            students = assignment.class_instance.students.all()
            for student in students:
                StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
        
        return Response({
            'id': assignment.id,
            'message': 'Assignment created successfully'
        }, status=201)
    
    @action(detail=False, methods=['post'])
    def create_draft(self, request):
        """Create draft assignment (Step 1)"""
        data = request.data
        
        # Validate basic fields
        required_fields = ['title', 'instructions', 'assignment_type', 'class_instance', 'due_date', 'max_score']
        for field in required_fields:
            if not data.get(field):
                return Response({'error': f'{field} is required'}, status=400)
        
        try:
            # Get the class instance
            from schools.models import Class
            class_instance = Class.objects.get(id=data['class_instance'])
            
            # Get current term (use is_current instead of is_active)
            current_term = Term.objects.filter(is_current=True).first()
            
            if not current_term:
                return Response({'error': 'No active academic term found. Please contact admin to set current term.'}, status=400)
            
            # Create draft assignment with all required fields
            assignment = Assignment.objects.create(
                title=data['title'],
                description=data['description'],
                instructions=data['instructions'],
                assignment_type=data['assignment_type'],
                class_instance=class_instance,
                term=current_term,
                created_by=request.user,
                due_date=data['due_date'],
                max_score=data['max_score'],
                max_attempts=data.get('max_attempts', 1),
                time_limit=data.get('time_limit'),
                is_timed=data.get('is_timed', False),
                auto_grade=data.get('auto_grade', False),
                allow_file_submission=data.get('allow_file_submission', True),
                allow_text_submission=data.get('allow_text_submission', True),
                status='DRAFT'
            )
            
            return Response({
                'id': assignment.id,
                'assignment_type': assignment.assignment_type,
                'next_step': self._get_next_step(assignment.assignment_type)
            })
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f'Failed to create assignment: {str(e)}'}, status=400)
    
    @action(detail=True, methods=['patch'])
    def update_configuration(self, request, pk=None):
        """Update assignment configuration (Step 2)"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        data = request.data
        assignment_type = assignment.assignment_type
        
        # Type-specific configuration
        if assignment_type in ['QUIZ', 'EXAM']:
            assignment.time_limit = data.get('time_limit')
            assignment.auto_grade = data.get('auto_grade', True)
            assignment.show_results_immediately = data.get('show_results_immediately', True)
        
        assignment.save()
        
        return Response({
            'id': assignment.id,
            'next_step': self._get_next_step(assignment_type, step=2)
        })
    
    @action(detail=True, methods=['get'], url_path='questions')
    def get_questions(self, request, pk=None):
        """Get questions for an assignment"""
        try:
            assignment = Assignment.objects.get(
                id=pk,
                created_by=request.user
            )
            
            # Return empty array for non-quiz assignments
            if assignment.assignment_type not in ['QUIZ', 'EXAM']:
                return Response([])
            
            questions = Question.objects.filter(
                assignment=assignment
            ).prefetch_related('options').order_by('order', 'id')
            
            question_data = []
            for question in questions:
                q_data = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'points': question.points,
                    'order': question.order,
                    'options': []
                }
                
                # Add MCQ options
                if question.question_type == 'mcq':
                    q_data['options'] = [{
                        'id': opt.id,
                        'option_text': opt.option_text,
                        'is_correct': opt.is_correct,
                        'order': opt.order
                    } for opt in question.options.all().order_by('order', 'id')]
                
                question_data.append(q_data)
            
            return Response(question_data)
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        except Exception as e:
            import traceback
            print(f"Error fetching questions: {e}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'], url_path='add-question')
    def add_question(self, request, pk=None):
        """Add question to assignment (Step 3)"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user
        )
        
        if assignment.assignment_type not in ['QUIZ', 'EXAM']:
            return Response({'error': 'Questions only allowed for Quiz/Exam'}, status=400)
        
        data = request.data
        
        # Validate required fields
        if not data.get('question_text'):
            return Response({'error': 'question_text is required'}, status=400)
        
        try:
            with transaction.atomic():
                question = Question.objects.create(
                    assignment=assignment,
                    question_text=data['question_text'],
                    question_type=data.get('question_type', 'mcq'),
                    points=data.get('points', 1),
                    order=assignment.questions.count() + 1
                )
                
                # Create MCQ options
                if data.get('question_type', 'mcq') == 'mcq':
                    options = data.get('options', [])
                    if not options:
                        return Response({'error': 'MCQ questions must have options'}, status=400)
                    
                    for idx, opt_data in enumerate(options):
                        QuestionOption.objects.create(
                            question=question,
                            option_text=opt_data.get('option_text', ''),
                            is_correct=opt_data.get('is_correct', False),
                            order=opt_data.get('order', idx + 1)
                        )
                
                return Response({
                    'question_id': question.id,
                    'total_questions': assignment.questions.count(),
                    'total_points': sum(q.points for q in assignment.questions.all())
                })
        except Exception as e:
            import traceback
            print(f"Error adding question: {e}")
            traceback.print_exc()
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def publish_assignment(self, request, pk=None):
        """Publish assignment - PRODUCTION FIXED for both DRAFT and PUBLISHED assignments"""
        try:
            assignment = Assignment.objects.get(
                id=pk,
                created_by=request.user
            )
            
            # Validate class_instance exists
            if not assignment.class_instance:
                return Response({
                    'error': 'Assignment must be assigned to a class before publishing. Please edit the assignment and select a class.'
                }, status=400)
            
            # Handle both DRAFT and already PUBLISHED assignments
            if assignment.status == 'DRAFT':
                # Validate assignment is ready for publishing
                total_points = None
                if assignment.assignment_type in ['QUIZ', 'EXAM']:
                    if not assignment.questions.exists():
                        return Response({'error': 'Quiz/Exam must have questions'}, status=400)
                    total_points = sum(q.points for q in assignment.questions.all())
                
                # Publish inside a single atomic block
                with transaction.atomic():
                    if total_points is not None:
                        assignment.max_score = total_points
                    assignment.status = 'PUBLISHED'
                    assignment.published_at = timezone.now()
                    assignment.save(skip_validation=True)  # skip full_clean, we validated manually
                    
                    # Auto-assign to all students in the class
                    students = assignment.class_instance.students.all()
                    assigned_count = 0
                    
                    for student in students:
                        try:
                            student_assignment, created = StudentAssignment.objects.get_or_create(
                                assignment=assignment,
                                student=student,
                                defaults={'status': 'NOT_STARTED'}
                            )
                            if created:
                                assigned_count += 1
                        except Exception as e:
                            print(f"Error assigning to student {student.id}: {e}")
                            continue
                    
                    return Response({
                        'id': assignment.id,
                        'message': 'Assignment published successfully',
                        'status': assignment.status,
                        'students_assigned': assigned_count
                    })
            
            elif assignment.status == 'PUBLISHED':
                # Assignment is already published - just ensure student assignments exist
                students = assignment.class_instance.students.all()
                assigned_count = 0
                
                for student in students:
                    try:
                        student_assignment, created = StudentAssignment.objects.get_or_create(
                            assignment=assignment,
                            student=student,
                            defaults={'status': 'NOT_STARTED'}
                        )
                        if created:
                            assigned_count += 1
                    except Exception as e:
                        print(f"Error assigning to student {student.id}: {e}")
                        continue
                
                return Response({
                    'id': assignment.id,
                    'message': 'Assignment is already published. Student assignments updated.',
                    'status': assignment.status,
                    'students_assigned': assigned_count
                })
            
            else:
                return Response({
                    'error': f'Cannot publish assignment with status: {assignment.status}'
                }, status=400)
            
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found or you do not have permission to publish it'}, status=404)
        except Exception as e:
            import traceback
            print(f"Error publishing assignment: {e}")
            traceback.print_exc()
            return Response({'error': f'Failed to publish assignment: {str(e)}'}, status=400)
    
    def _get_next_step(self, assignment_type, step=1):
        """Determine next step based on assignment type"""
        if step == 1:
            if assignment_type == 'HOMEWORK':
                return 'review'
            elif assignment_type == 'PROJECT':
                return 'project_config'
            elif assignment_type in ['QUIZ', 'EXAM']:
                return 'quiz_config'
        elif step == 2:
            if assignment_type in ['QUIZ', 'EXAM']:
                return 'questions'
            else:
                return 'review'
        return 'review'
    
    @action(detail=True, methods=['get'], url_path='submissions')
    def get_submissions(self, request, pk=None):
        """Get all student submissions for an assignment"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        submissions = StudentAssignment.objects.filter(
            assignment=assignment
        ).select_related('student').order_by('student__first_name')
        
        submission_data = []
        for submission in submissions:
            submission_data.append({
                'id': submission.id,
                'student': {
                    'id': submission.student.id,
                    'name': submission.student.get_full_name(),
                    'student_id': submission.student.student_id
                },
                'status': submission.status,
                'submitted_at': submission.submitted_at,
                'score': submission.score,
                'attempts_count': submission.attempts_count,
                'is_overdue': assignment.due_date < timezone.now() if assignment.due_date else False,
                'can_reopen': submission.status in ['NOT_STARTED', 'EXPIRED'] or (assignment.due_date < timezone.now() and submission.status == 'NOT_STARTED')
            })
        
        return Response({
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'due_date': assignment.due_date,
                'max_score': assignment.max_score
            },
            'submissions': submission_data
        })
    
    @action(detail=True, methods=['post'], url_path='reopen-submission')
    def reopen_submission(self, request, pk=None):
        """Reopen assignment for a specific student"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'error': 'student_id required'}, status=400)
        
        try:
            submission = StudentAssignment.objects.get(
                assignment=assignment,
                student_id=student_id
            )
            
            # Reset submission status
            submission.status = 'NOT_STARTED'
            submission.submitted_at = None
            submission.score = None
            submission.teacher_feedback = ''
            submission.save()
            
            # Send notification
            self._send_reopen_notification(submission.student, assignment)
            
            return Response({
                'message': f'Assignment reopened for {submission.student.get_full_name()}',
                'submission': {
                    'id': submission.id,
                    'status': submission.status
                }
            })
            
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
    
    @action(detail=True, methods=['post'], url_path='extend-deadline')
    def extend_deadline(self, request, pk=None):
        """Extend assignment deadline"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        new_due_date = request.data.get('new_due_date')
        if not new_due_date:
            return Response({'error': 'new_due_date required'}, status=400)
        
        assignment.due_date = new_due_date
        assignment.save()
        
        return Response({
            'message': 'Assignment deadline extended',
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'due_date': assignment.due_date
            }
        })
    
    @action(detail=True, methods=['post'], url_path='bulk-reopen')
    def bulk_reopen_submissions(self, request, pk=None):
        """Reopen assignment for multiple students"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        student_ids = request.data.get('student_ids', [])
        if not student_ids:
            return Response({'error': 'student_ids required'}, status=400)
        
        reopened_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                submission = StudentAssignment.objects.get(
                    assignment=assignment,
                    student_id=student_id
                )
                submission.status = 'NOT_STARTED'
                submission.submitted_at = None
                submission.score = None
                submission.teacher_feedback = ''
                submission.save()
                
                # Send notification
                self._send_reopen_notification(submission.student, assignment)
                reopened_count += 1
                
            except StudentAssignment.DoesNotExist:
                errors.append(f'Submission not found for student {student_id}')
            except Exception as e:
                errors.append(f'Error reopening for student {student_id}: {str(e)}')
        
        return Response({
            'message': f'Reopened assignments for {reopened_count} students',
            'reopened_count': reopened_count,
            'errors': errors
        })
    
    @action(detail=True, methods=['post'], url_path='extend-individual-deadline')
    def extend_individual_deadline(self, request, pk=None):
        """Extend deadline for individual student"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        student_id = request.data.get('student_id')
        new_due_date = request.data.get('new_due_date')
        
        if not student_id or not new_due_date:
            return Response({'error': 'student_id and new_due_date required'}, status=400)
        
        try:
            submission = StudentAssignment.objects.get(
                assignment=assignment,
                student_id=student_id
            )
            
            # Store individual deadline in additional_files field as JSON
            import json
            try:
                additional_data = json.loads(submission.additional_files) if submission.additional_files else {}
            except:
                additional_data = {}
            
            additional_data['individual_due_date'] = new_due_date
            submission.additional_files = json.dumps(additional_data)
            submission.save()
            
            return Response({
                'message': f'Individual deadline extended for {submission.student.get_full_name()}',
                'submission': {
                    'id': submission.id,
                    'individual_due_date': new_due_date
                }
            })
            
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
    
    def _send_reopen_notification(self, student, assignment):
        """Send notification when assignment is reopened"""
        try:
            from notifications.models import Notification
            
            Notification.objects.create(
                user=student.user,
                title=f'Assignment Reopened: {assignment.title}',
                message=f'Your teacher has reopened the assignment "{assignment.title}". You can now submit your work.',
                type='assignment_reopened',
                assignment_id=assignment.id
            )
        except Exception as e:
            print(f'Failed to send notification: {e}')
    
    @action(detail=True, methods=['patch'], url_path='grade-submission')
    def grade_submission(self, request, pk=None):
        """Grade a student submission"""
        assignment = get_object_or_404(
            Assignment, 
            id=pk, 
            created_by=request.user
        )
        
        submission_id = request.data.get('submission_id')
        score = request.data.get('score')
        feedback = request.data.get('feedback', '')
        
        if not submission_id:
            return Response({'error': 'submission_id required'}, status=400)
        
        if score is None:
            return Response({'error': 'score required'}, status=400)
        
        # Get and verify submission
        submission = get_object_or_404(
            StudentAssignment,
            id=submission_id,
            assignment=assignment
        )
        
        # Update submission
        submission.score = score
        submission.teacher_feedback = feedback
        submission.status = 'GRADED'
        submission.graded_at = timezone.now()
        submission.save()
        
        # Return serialized submission
        serializer = StudentAssignmentSerializer(submission)
        return Response(serializer.data)


class StudentAssignmentViewSet(viewsets.ViewSet):
    """Clean API for students to access assignments"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='my-assignments')
    def my_assignments(self, request):
        """Get student's assignments - PRODUCTION FIXED with comprehensive error handling"""
        try:
            student = Student.objects.select_related('current_class').get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        class_id = request.query_params.get('class_id')
        
        try:
            # PRODUCTION FIX: More robust assignment fetching
            if class_id:
                # Get assignments for specific class
                try:
                    target_class = Class.objects.get(id=class_id)
                    # Verify student has access to this class
                    if student.current_class != target_class:
                        return Response({'error': 'Access denied to this class'}, status=403)
                    published_assignments = Assignment.objects.filter(
                        class_instance=target_class,
                        status='PUBLISHED'
                    ).select_related('class_subject__subject')
                except Class.DoesNotExist:
                    return Response({'error': 'Class not found'}, status=404)
            else:
                # Get assignments for student's current class
                if not student.current_class:
                    return Response([], status=200)  # No class assigned
                
                published_assignments = Assignment.objects.filter(
                    class_instance=student.current_class,
                    status='PUBLISHED'
                ).select_related('class_subject__subject')
            
            print(f"STUDENT ASSIGNMENT DEBUG:")
            print(f"  Student: {student.get_full_name()} (ID: {student.id})")
            print(f"  Student Class: {student.current_class}")
            print(f"  Class ID param: {class_id}")
            print(f"  Published assignments found: {published_assignments.count()}")
            
            # CRITICAL FIX: Auto-create missing StudentAssignment records
            created_count = 0
            for assignment in published_assignments:
                try:
                    student_assignment, created = StudentAssignment.objects.get_or_create(
                        assignment=assignment,
                        student=student,
                        defaults={'status': 'NOT_STARTED'}
                    )
                    if created:
                        created_count += 1
                        print(f"  AUTO-CREATED: StudentAssignment for '{assignment.title}'")
                except Exception as e:
                    print(f"  ERROR creating StudentAssignment for '{assignment.title}': {e}")
                    continue
            
            if created_count > 0:
                print(f"  Auto-created {created_count} missing StudentAssignment records")
            
            # Get all student assignments (including newly created ones)
            student_assignments = StudentAssignment.objects.filter(
                student=student,
                assignment__status='PUBLISHED'
            ).select_related('assignment', 'assignment__class_subject__subject')
            
            # Additional filtering by class if specified
            if class_id:
                student_assignments = student_assignments.filter(
                    assignment__class_instance_id=class_id
                )
            
            print(f"  Final StudentAssignment count: {student_assignments.count()}")
            
            # Build response data
            assignment_data = []
            for sa in student_assignments:
                try:
                    assignment_data.append({
                        'id': sa.assignment.id,
                        'title': sa.assignment.title,
                        'description': sa.assignment.description,
                        'subject_name': sa.assignment.class_subject.subject.name if sa.assignment.class_subject else 'General',
                        'subject_id': sa.assignment.class_subject.subject.id if sa.assignment.class_subject else None,
                        'assignment_type': sa.assignment.assignment_type,
                        'due_date': sa.assignment.due_date,
                        'points': sa.assignment.max_score,
                        'status': sa.status,
                        'score': sa.score,
                        'time_limit': sa.assignment.time_limit,
                        'max_attempts': sa.assignment.max_attempts,
                        'submitted_at': sa.submitted_at,
                        'teacher_feedback': sa.teacher_feedback,
                        'class_name': str(sa.assignment.class_instance) if sa.assignment.class_instance else 'Unknown Class'
                    })
                except Exception as e:
                    print(f"  ERROR serializing assignment {sa.assignment.id}: {e}")
                    continue
            
            print(f"  Returning {len(assignment_data)} assignments to frontend")
            return Response(assignment_data)
            
        except Exception as e:
            print(f"CRITICAL ERROR in my_assignments: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list instead of error to prevent frontend crashes
            return Response([], status=200)
    
    @action(detail=False, methods=['get'], url_path='submission-stats')
    def submission_stats(self, request):
        """Get student's submission statistics"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        )
        
        from django.utils import timezone
        now = timezone.now()
        
        total = assignments.count()
        submitted = assignments.filter(status__in=['SUBMITTED', 'GRADED']).count()
        pending = assignments.filter(status='NOT_STARTED').count()
        overdue = assignments.filter(
            assignment__due_date__lt=now,
            status='NOT_STARTED'
        ).count()
        
        return Response({
            'total': total,
            'submitted': submitted,
            'pending': pending,
            'overdue': overdue
        })
    

    
    @action(detail=True, methods=['get'])
    def take(self, request, pk=None):
        """Get assignment for student to take - PRODUCTION FIXED"""
        try:
            student = Student.objects.select_related('current_class').get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        # Get assignment with proper error handling
        try:
            assignment = Assignment.objects.select_related('class_instance').get(
                id=pk, 
                status='PUBLISHED'
            )
        except Assignment.DoesNotExist:
            return Response({
                'error': 'Assignment not found or not published',
                'assignment_id': pk
            }, status=404)
        
        # PRODUCTION FIX: Robust access verification with multiple fallbacks
        has_access = False
        access_method = None
        
        # Method 1: Direct class comparison
        if student.current_class and assignment.class_instance:
            if student.current_class.id == assignment.class_instance.id:
                has_access = True
                access_method = 'direct_class_match'
        
        # Method 2: Check if student is enrolled in assignment's class
        if not has_access and assignment.class_instance:
            if assignment.class_instance.students.filter(id=student.id).exists():
                has_access = True
                access_method = 'enrollment_check'
        
        # Method 3: Check if student has existing StudentAssignment record
        if not has_access:
            if StudentAssignment.objects.filter(
                assignment=assignment,
                student=student
            ).exists():
                has_access = True
                access_method = 'existing_assignment'
        
        # PRODUCTION LOGGING for debugging
        print(f"Assignment Access Check - Student: {student.id}, Assignment: {assignment.id}")
        print(f"Student Class: {student.current_class.id if student.current_class else None}")
        print(f"Assignment Class: {assignment.class_instance.id if assignment.class_instance else None}")
        print(f"Access Granted: {has_access} via {access_method}")
        
        if not has_access:
            return Response({
                'error': 'Access denied - you are not enrolled in this class',
                'debug': {
                    'student_id': student.id,
                    'student_class_id': student.current_class.id if student.current_class else None,
                    'assignment_id': assignment.id,
                    'assignment_class_id': assignment.class_instance.id if assignment.class_instance else None,
                    'assignment_title': assignment.title
                }
            }, status=403)
        
        # Get or create StudentAssignment
        student_assignment, created = StudentAssignment.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'status': 'NOT_STARTED'}
        )
        
        if created:
            print(f"Created new StudentAssignment for student {student.id}, assignment {assignment.id}")
        
        # Check if already completed
        if student_assignment.status == 'GRADED':
            # Return the graded result instead of blocking
            return Response({
                'assignment': {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'assignment_type': assignment.assignment_type,
                    'due_date': assignment.due_date,
                    'time_limit': assignment.time_limit,
                    'is_timed': assignment.is_timed,
                    'max_score': assignment.max_score,
                    'max_attempts': assignment.max_attempts
                },
                'questions': [],
                'student_assignment': {
                    'id': student_assignment.id,
                    'status': student_assignment.status,
                    'score': student_assignment.score,
                    'attempts_count': student_assignment.attempts_count
                }
            })
        
        # Get questions with proper ordering
        questions = Question.objects.filter(
            assignment=assignment
        ).prefetch_related('options').order_by('order', 'id')
        
        question_data = []
        for question in questions:
            q_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points,
                'order': question.order
            }
            
            # Add MCQ options
            if question.question_type == 'mcq':
                q_data['options'] = [{
                    'id': opt.id,
                    'option_text': opt.option_text,
                    'order': opt.order
                } for opt in question.options.all().order_by('order', 'id')]
            
            question_data.append(q_data)
        
        # PRODUCTION FIX: Return structure matching frontend expectations
        return Response({
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'assignment_type': assignment.assignment_type,
                'due_date': assignment.due_date,
                'time_limit': assignment.time_limit,
                'is_timed': assignment.is_timed,
                'max_score': assignment.max_score,
                'max_attempts': assignment.max_attempts
            },
            'questions': question_data,
            'student_assignment': {
                'id': student_assignment.id,
                'status': student_assignment.status,
                'attempts_count': student_assignment.attempts_count
            }
        })
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit assignment answers"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        assignment = get_object_or_404(Assignment, id=pk)
        student_assignment = get_object_or_404(
            StudentAssignment,
            assignment=assignment,
            student=student
        )
        
        answers_data = request.data.get('answers', [])
        
        with transaction.atomic():
            if assignment.assignment_type in ['QUIZ', 'EXAM']:
                # Handle quiz submission
                attempt, created = QuizAttempt.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'IN_PROGRESS'}
                )
                
                total_points = 0
                earned_points = 0
                
                for answer_data in answers_data:
                    question = get_object_or_404(Question, id=answer_data['question_id'])
                    
                    quiz_answer, created = QuizAnswer.objects.get_or_create(
                        attempt=attempt,
                        question=question
                    )
                    
                    if question.question_type == 'mcq':
                        quiz_answer.selected_option_id = answer_data.get('selected_option_id')
                    else:
                        quiz_answer.answer_text = answer_data.get('answer_text', '')
                    
                    quiz_answer.check_answer()
                    
                    total_points += question.points
                    earned_points += quiz_answer.points_earned
                
                # Calculate score
                final_score = (earned_points / total_points) * assignment.max_score if total_points > 0 else 0
                
                attempt.score = final_score
                attempt.status = 'SUBMITTED'
                attempt.submitted_at = timezone.now()
                attempt.save()
                
                student_assignment.score = final_score
                student_assignment.status = 'GRADED'
                student_assignment.submitted_at = timezone.now()
                student_assignment.save()
                
                return Response({
                    'message': 'Assignment submitted successfully',
                    'score': final_score,
                    'status': 'GRADED'
                })
            
            else:
                # Handle regular assignment
                student_assignment.submission_text = request.data.get('submission_text', '')
                student_assignment.status = 'SUBMITTED'
                student_assignment.submitted_at = timezone.now()
                student_assignment.save()
                
                return Response({
                    'message': 'Assignment submitted successfully',
                    'status': 'SUBMITTED'
                })
    
    @action(detail=False, methods=['get'], url_path='my-classes')
    def my_classes(self, request):
        """Get student's classes"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        if student.current_class:
            return Response([{
                'id': student.current_class.id,
                'name': str(student.current_class),
                'level': student.current_class.level,
                'section': student.current_class.section or '',
                'class_teacher': student.current_class.class_teacher.get_full_name() if student.current_class.class_teacher else None,
                'assignment_count': Assignment.objects.filter(
                    class_instance=student.current_class,
                    status='PUBLISHED'
                ).count(),
                'pending_count': StudentAssignment.objects.filter(
                    student=student,
                    assignment__class_instance=student.current_class,
                    status='NOT_STARTED'
                ).count()
            }])
        return Response([])
    
    @action(detail=False, methods=['get'], url_path='class-subjects')
    def class_subjects(self, request):
        """Get subjects for a class"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        class_id = request.query_params.get('class_id')
        if not class_id:
            return Response({'error': 'class_id parameter required'}, status=400)
        
        from schools.models import ClassSubject
        class_subjects = ClassSubject.objects.filter(
            class_instance_id=class_id
        ).select_related('subject', 'teacher')
        
        subjects = []
        for cs in class_subjects:
            subjects.append({
                'id': cs.subject.id,
                'name': cs.subject.name,
                'code': cs.subject.code,
                'teacher': cs.teacher.get_full_name() if cs.teacher else 'No Teacher Assigned',
                'category': cs.subject.category
            })
        
        return Response(subjects)
    
    @action(detail=False, methods=['get'], url_path='class-announcements')
    def class_announcements(self, request):
        """Get announcements for a class"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        class_id = request.query_params.get('class_id')
        if not class_id:
            return Response({'error': 'class_id parameter required'}, status=400)
        
        from notifications.models import Notification
        notifications = Notification.objects.filter(
            user=request.user,
            read=False
        ).order_by('-created_at')[:10]
        
        announcements = []
        for notif in notifications:
            announcements.append({
                'id': notif.id,
                'title': notif.title,
                'content': notif.message,
                'date': notif.created_at.isoformat(),
                'priority': 'high' if notif.type == 'error' else 'medium',
                'read': notif.read,
                'is_read': notif.read
            })
        
        return Response(announcements)
    
    @action(detail=True, methods=['get'], url_path='submission')
    def get_submission(self, request, pk=None):
        """Get student's submission for an assignment"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        try:
            assignment = Assignment.objects.get(id=pk, status='PUBLISHED')
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
            
            # Get quiz answers if it's a quiz/exam
            answers = {}
            if assignment.assignment_type in ['QUIZ', 'EXAM']:
                try:
                    quiz_attempt = QuizAttempt.objects.get(
                        assignment=assignment,
                        student=student
                    )
                    quiz_answers = QuizAnswer.objects.filter(attempt=quiz_attempt)
                    for qa in quiz_answers:
                        if qa.selected_option:
                            answers[qa.question.id] = qa.selected_option.id
                        else:
                            answers[qa.question.id] = qa.answer_text
                except QuizAttempt.DoesNotExist:
                    pass
            
            return Response({
                'id': student_assignment.id,
                'status': student_assignment.status,
                'submitted_at': student_assignment.submitted_at,
                'score': student_assignment.score,
                'answers': answers
            })
            
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'No submission found'}, status=404)
    
    @action(detail=True, methods=['post'], url_path='save')
    def save_submission(self, request, pk=None):
        """Save student's work in progress"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        try:
            assignment = Assignment.objects.get(id=pk, status='PUBLISHED')
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        
        student_assignment, created = StudentAssignment.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'status': 'IN_PROGRESS'}
        )
        
        # Update status to in progress if not already submitted
        if student_assignment.status == 'NOT_STARTED':
            student_assignment.status = 'IN_PROGRESS'
            student_assignment.save()
        
        return Response({'message': 'Progress saved successfully'})
