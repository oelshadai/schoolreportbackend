"""
Academically Correct VClass Workflow API
Mandatory subject selection, instructions field, preview step
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from schools.models import Class, ClassSubject
from .models import Assignment, Question, QuestionOption, StudentAssignment
from .serializers import AssignmentSerializer


class AcademicWorkflowViewSet(viewsets.ViewSet):
    """Academically correct assignment workflow"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='start')
    def start_workflow(self, request):
        """Step 1: Create draft with MANDATORY class + subject + term"""
        data = request.data
        
        # Academic validation - ALL required (updated for subject_name)
        required = ['title', 'description', 'instructions', 'assignment_type', 'class_instance', 'due_date', 'max_score']
        for field in required:
            if not data.get(field):
                return Response({'error': f'{field} is academically required'}, status=400)
        
        # Get current term - REQUIRED for academic structure
        from schools.models import Term
        try:
            current_term = Term.objects.filter(
                school=request.user.school,
                is_current=True
            ).first()
            
            if not current_term:
                # Fallback: get most recent term
                current_term = Term.objects.filter(
                    school=request.user.school
                ).order_by('-start_date').first()
                
            if not current_term:
                return Response({'error': 'No active term found. Please contact administrator.'}, status=400)
                
        except Exception as e:
            return Response({'error': f'Term validation failed: {str(e)}'}, status=400)
        
        # Handle subject - either subject_name or class_subject ID
        if data.get('subject_name'):
            # Create or get subject by name
            from schools.models import Subject
            subject, created = Subject.objects.get_or_create(
                name=data['subject_name'].strip()
            )
            
            # Create or get ClassSubject for this teacher
            class_subject, created = ClassSubject.objects.get_or_create(
                class_instance_id=data['class_instance'],
                subject=subject,
                teacher=request.user
            )
        elif data.get('class_subject'):
            # Validate teacher owns this subject in this class
            try:
                class_subject = ClassSubject.objects.get(
                    id=data['class_subject'],
                    class_instance_id=data['class_instance'],
                    teacher=request.user
                )
            except ClassSubject.DoesNotExist:
                return Response({'error': 'You do not teach this subject in this class'}, status=403)
        else:
            return Response({'error': 'Subject is required (subject_name or class_subject)'}, status=400)
        
        # WORKFLOW-SAFE CREATION: Create DRAFT with minimal validation
        try:
            assignment = Assignment.objects.create(
                title=data['title'],
                description=data['description'],
                instructions=data['instructions'],  # Now mandatory
                assignment_type=data['assignment_type'],
                class_instance_id=data['class_instance'],
                class_subject=class_subject,  # Now mandatory
                term=current_term,  # Now mandatory
                created_by=request.user,
                due_date=data['due_date'],
                max_score=data['max_score'],
                max_attempts=1,  # Default safe value
                status='DRAFT'  # DRAFT allows incomplete configuration
            )
        except Exception as e:
            return Response({'error': f'Assignment creation failed: {str(e)}'}, status=500)
        
        return Response({
            'workflow_id': assignment.id,
            'assignment_type': assignment.assignment_type,
            'next_step': self._get_next_step(assignment.assignment_type),
            'academic_validation': 'passed',
            'term': current_term.name
        })
    
    @action(detail=True, methods=['patch'], url_path='configure')
    def configure_type_specific(self, request, pk=None):
        """Step 2: TYPE-SPECIFIC dynamic configuration"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        data = request.data
        assignment_type = assignment.assignment_type
        
        # TYPE-SPECIFIC ACADEMIC LOGIC
        if assignment_type == 'HOMEWORK':
            # Homework: Text + optional file
            assignment.allow_text_submission = True
            assignment.allow_file_submission = data.get('allow_file_submission', True)
            assignment.max_file_size = data.get('max_file_size', 10)
            assignment.allowed_file_types = data.get('allowed_file_types', 'pdf,doc,docx,txt')
        
        elif assignment_type == 'PROJECT':
            # Project: File mandatory, larger sizes, rubric support
            assignment.allow_file_submission = True  # Mandatory for projects
            assignment.allow_text_submission = data.get('allow_text_submission', True)
            assignment.max_file_size = data.get('max_file_size', 50)  # Larger for projects
            assignment.allowed_file_types = data.get('allowed_file_types', 'pdf,doc,docx,zip,jpg,png')
            # TODO: Add rubric support
        
        elif assignment_type == 'QUIZ':
            # Quiz: Timed, auto-grade, multiple attempts possible
            assignment.time_limit = data.get('time_limit', 30)  # Default 30 min
            assignment.max_attempts = data.get('max_attempts', 3)  # Default 3 attempts
            assignment.is_timed = True
            assignment.auto_grade = True
            assignment.show_results_immediately = data.get('show_results_immediately', True)
            assignment.allow_file_submission = False  # No files in quiz
            assignment.allow_text_submission = False  # Only MCQ/short answer
        
        elif assignment_type == 'EXAM':
            # Exam: Strict time, one attempt, auto-submit
            assignment.time_limit = data.get('time_limit', 60)  # Default 60 min
            assignment.max_attempts = 1  # EXAM ENFORCEMENT: Single attempt only
            assignment.is_timed = True
            assignment.auto_grade = True
            assignment.show_results_immediately = False  # Hide results for exams
            assignment.allow_file_submission = False  # No files in exam
            assignment.allow_text_submission = False  # Only questions
        
        assignment.save()
        
        return Response({
            'workflow_id': assignment.id,
            'next_step': self._get_next_step(assignment_type, step=2),
            'type_configured': assignment_type
        })
    
    @action(detail=True, methods=['post'], url_path='questions')
    def add_question(self, request, pk=None):
        """Step 3: Add questions (QUIZ/EXAM only)"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        if assignment.assignment_type not in ['QUIZ', 'EXAM']:
            return Response({'error': 'Questions only for Quiz/Exam types'}, status=400)
        
        data = request.data
        
        # Academic validation for questions
        if not data.get('question_text', '').strip():
            return Response({'error': 'Question text is required'}, status=400)
        
        if data.get('points', 0) <= 0:
            return Response({'error': 'Question points must be > 0'}, status=400)
        
        with transaction.atomic():
            question = Question.objects.create(
                assignment=assignment,
                question_text=data['question_text'],
                question_type=data['question_type'],
                points=data.get('points', 1),
                order=assignment.questions.count() + 1
            )
            
            # MCQ validation
            if data['question_type'] == 'mcq':
                options = data.get('options', [])
                if len(options) < 2:
                    return Response({'error': 'MCQ needs at least 2 options'}, status=400)
                
                correct_count = sum(1 for opt in options if opt.get('is_correct'))
                if correct_count != 1:
                    return Response({'error': 'MCQ needs exactly 1 correct answer'}, status=400)
                
                for i, opt_data in enumerate(options):
                    if not opt_data.get('option_text', '').strip():
                        return Response({'error': f'Option {i+1} text is required'}, status=400)
                    
                    QuestionOption.objects.create(
                        question=question,
                        option_text=opt_data['option_text'],
                        is_correct=opt_data['is_correct'],
                        order=i
                    )
        
        # Academic point validation
        total_questions = assignment.questions.count()
        total_points = sum(q.points for q in assignment.questions.all())
        points_match = total_points == assignment.max_score
        
        return Response({
            'question_id': question.id,
            'total_questions': total_questions,
            'total_points': total_points,
            'max_score': assignment.max_score,
            'points_match': points_match,
            'can_preview': points_match if assignment.assignment_type in ['QUIZ', 'EXAM'] else True
        })
    
    @action(detail=True, methods=['get'], url_path='preview')
    def preview_assignment(self, request, pk=None):
        """Step 4: PREVIEW - Show exactly how student will see it"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        # Academic validation before preview
        validation_errors = self._validate_for_preview(assignment)
        if validation_errors:
            return Response({'errors': validation_errors}, status=400)
        
        # Update preview status
        assignment.status = 'PREVIEW'
        assignment.previewed_at = timezone.now()
        assignment.save()
        
        # Generate EXACT student view
        preview_data = {
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'instructions': assignment.instructions,
                'assignment_type': assignment.assignment_type,
                'class_name': str(assignment.class_instance),
                'subject_name': assignment.class_subject.subject.name,
                'due_date': assignment.due_date,
                'max_score': assignment.max_score,
                'time_limit': assignment.time_limit,
                'is_timed': assignment.is_timed
            },
            'student_view': self._generate_student_preview(assignment),
            'validation': {'valid': True, 'errors': []}
        }
        
        # Add questions for quiz/exam
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            questions = assignment.questions.prefetch_related('options').order_by('order')
            preview_data['questions'] = [{
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'points': q.points,
                'options': [{
                    'id': opt.id,
                    'option_text': opt.option_text,
                    'order': opt.order
                    # Hide is_correct in preview
                } for opt in q.options.all()] if q.question_type == 'mcq' else []
            } for q in questions]
        
        return Response(preview_data)
    
    @action(detail=True, methods=['post'], url_path='publish')
    def publish_assignment(self, request, pk=None):
        """Step 5: PUBLISH - Final academic validation and enforcement"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='PREVIEW'  # Must be previewed first
        )
        
        # Final academic validation
        validation_errors = self._validate_for_publish(assignment)
        if validation_errors:
            return Response({'errors': validation_errors}, status=400)
        
        # ACADEMIC ENFORCEMENT: Apply strict rules before publishing
        try:
            # Enforce type-specific rules
            if assignment.assignment_type == 'PROJECT':
                assignment.allow_file_submission = True  # Force file submission for projects
            
            elif assignment.assignment_type in ['QUIZ', 'EXAM']:
                if not assignment.time_limit or assignment.time_limit <= 0:
                    return Response({'error': f'{assignment.assignment_type} must have a valid time limit'}, status=400)
                assignment.is_timed = True  # Force timed for quiz/exam
            
            if assignment.assignment_type == 'EXAM':
                assignment.max_attempts = 1  # Force single attempt for exams
            
            # Publish with academic integrity
            with transaction.atomic():
                assignment.status = 'PUBLISHED'
                assignment.published_at = timezone.now()
                assignment.save()  # This will trigger clean() validation for PUBLISHED status
                
                # Auto-assign to ALL students in class
                students = assignment.class_instance.students.all()
                for student in students:
                    StudentAssignment.objects.get_or_create(
                        assignment=assignment,
                        student=student,
                        defaults={'status': 'NOT_STARTED'}
                    )
        
        except ValidationError as e:
            return Response({'error': f'Academic validation failed: {str(e)}'}, status=400)
        except Exception as e:
            return Response({'error': f'Publishing failed: {str(e)}'}, status=500)
        
        return Response({
            'id': assignment.id,
            'message': 'Assignment published successfully',
            'students_assigned': students.count(),
            'published_at': assignment.published_at,
            'academic_status': 'valid'
        })
    
    def _get_next_step(self, assignment_type, step=1):
        """Academic workflow steps"""
        flows = {
            'HOMEWORK': ['basic_info', 'homework_settings', 'preview', 'publish'],
            'PROJECT': ['basic_info', 'project_settings', 'preview', 'publish'],
            'QUIZ': ['basic_info', 'quiz_settings', 'questions', 'preview', 'publish'],
            'EXAM': ['basic_info', 'exam_settings', 'questions', 'preview', 'publish']
        }
        
        flow = flows.get(assignment_type, flows['HOMEWORK'])
        if step < len(flow):
            return flow[step]
        return 'publish'
    
    def _validate_for_preview(self, assignment):
        """Academic validation before preview"""
        errors = []
        
        if not assignment.title.strip():
            errors.append('Title is required')
        
        if not assignment.description.strip():
            errors.append('Description is required')
        
        if not assignment.instructions.strip():
            errors.append('Instructions are required for academic clarity')
        
        if not assignment.class_subject:
            errors.append('Subject assignment is mandatory')
        
        # Type-specific validation
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            if not assignment.questions.exists():
                errors.append(f'{assignment.assignment_type} must have questions')
            else:
                total_points = sum(q.points for q in assignment.questions.all())
                if total_points != assignment.max_score:
                    errors.append(f'Question points ({total_points}) must equal max score ({assignment.max_score})')
        
        return errors
    
    def _validate_for_publish(self, assignment):
        """Final academic validation"""
        errors = self._validate_for_preview(assignment)
        
        if assignment.status != 'PREVIEW':
            errors.append('Assignment must be previewed before publishing')
        
        return errors
    
    def _generate_student_preview(self, assignment):
        """Generate exact student view"""
        submission_types = []
        if assignment.allow_text_submission:
            submission_types.append('Text Response')
        if assignment.allow_file_submission:
            submission_types.append(f'File Upload (max {assignment.max_file_size}MB)')
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            submission_types.append('Online Questions')
        
        return {
            'title': assignment.title,
            'description': assignment.description,
            'instructions': assignment.instructions,
            'subject': assignment.class_subject.subject.name,
            'due_date': assignment.due_date.strftime('%B %d, %Y at %I:%M %p'),
            'points': f"{assignment.max_score} points",
            'time_limit': f"{assignment.time_limit} minutes" if assignment.time_limit else "No time limit",
            'submission_types': submission_types
        }