"""
Enhanced VClass Workflow API with Preview and Subject Support
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

class EnhancedWorkflowViewSet(viewsets.ViewSet):
    """Enhanced workflow with subject selection and preview"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='start')
    def start_workflow(self, request):
        """Step 1: Create draft with class + subject selection"""
        data = request.data
        
        # Validate required fields including subject
        required = ['title', 'description', 'instructions', 'assignment_type', 'class_instance', 'class_subject', 'due_date', 'max_score']
        for field in required:
            if not data.get(field):
                return Response({'error': f'{field} is required'}, status=400)
        
        # Validate subject belongs to class
        class_subject = get_object_or_404(ClassSubject, id=data['class_subject'])
        if class_subject.class_instance_id != int(data['class_instance']):
            return Response({'error': 'Subject does not belong to selected class'}, status=400)
        
        # Create draft assignment
        assignment = Assignment.objects.create(
            title=data['title'],
            description=data['description'],
            instructions=data['instructions'],
            assignment_type=data['assignment_type'],
            class_instance_id=data['class_instance'],
            class_subject=class_subject,
            created_by=request.user,
            due_date=data['due_date'],
            max_score=data['max_score'],
            status='DRAFT'
        )
        
        return Response({
            'workflow_id': assignment.id,
            'assignment_type': assignment.assignment_type,
            'next_step': self._get_next_step(assignment.assignment_type),
            'step_config': self._get_step_config(assignment.assignment_type)
        })
    
    @action(detail=True, methods=['patch'], url_path='configure')
    def configure_settings(self, request, pk=None):
        """Step 2: Type-specific dynamic configuration"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        data = request.data
        assignment_type = assignment.assignment_type
        
        # Type-specific dynamic expansion
        if assignment_type == 'HOMEWORK':
            assignment.allow_file_submission = data.get('allow_file_submission', True)
            assignment.allow_text_submission = data.get('allow_text_submission', True)
            assignment.max_file_size = data.get('max_file_size', 10)
            assignment.allowed_file_types = data.get('allowed_file_types', 'pdf,doc,docx,txt')
        
        elif assignment_type == 'PROJECT':
            assignment.allow_file_submission = data.get('allow_file_submission', True)
            assignment.max_file_size = data.get('max_file_size', 50)
            assignment.allowed_file_types = data.get('allowed_file_types', 'pdf,doc,docx,zip,jpg,png')
            # Add rubric criteria (to be implemented)
            
        elif assignment_type in ['QUIZ', 'EXAM']:
            assignment.time_limit = data.get('time_limit')
            assignment.is_timed = bool(data.get('time_limit'))
            assignment.auto_grade = data.get('auto_grade', True)
            assignment.show_results_immediately = data.get('show_results_immediately', True)
        
        assignment.save()
        
        return Response({
            'workflow_id': assignment.id,
            'next_step': self._get_next_step(assignment_type, step=2),
            'configuration_saved': True
        })
    
    @action(detail=True, methods=['post'], url_path='questions')
    def add_question(self, request, pk=None):
        """Step 3: Add questions with enhanced validation"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        if assignment.assignment_type not in ['QUIZ', 'EXAM']:
            return Response({'error': 'Questions only for Quiz/Exam'}, status=400)
        
        data = request.data
        
        with transaction.atomic():
            question = Question.objects.create(
                assignment=assignment,
                question_text=data['question_text'],
                question_type=data['question_type'],
                points=data.get('points', 1),
                order=assignment.questions.count() + 1
            )
            
            # Enhanced MCQ options with validation
            if data['question_type'] == 'mcq':
                options = data.get('options', [])
                if len(options) < 2:
                    return Response({'error': 'MCQ must have at least 2 options'}, status=400)
                
                correct_count = sum(1 for opt in options if opt.get('is_correct'))
                if correct_count != 1:
                    return Response({'error': 'MCQ must have exactly 1 correct answer'}, status=400)
                
                for opt_data in options:
                    QuestionOption.objects.create(
                        question=question,
                        option_text=opt_data['option_text'],
                        is_correct=opt_data['is_correct'],
                        order=opt_data.get('order', 0)
                    )
        
        total_questions = assignment.questions.count()
        total_points = sum(q.points for q in assignment.questions.all())
        
        return Response({
            'question_id': question.id,
            'total_questions': total_questions,
            'total_points': total_points,
            'points_match': total_points == assignment.max_score
        })
    
    @action(detail=True, methods=['get'], url_path='preview')
    def preview_assignment(self, request, pk=None):
        """Step 4: Preview assignment before publishing"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        # Update preview timestamp
        assignment.previewed_at = timezone.now()
        assignment.status = 'PREVIEW'
        assignment.save()
        
        # Build preview data
        preview_data = {
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'instructions': assignment.instructions,
                'assignment_type': assignment.assignment_type,
                'class_name': str(assignment.class_instance),
                'subject_name': assignment.class_subject.subject.name if assignment.class_subject else 'No Subject',
                'due_date': assignment.due_date,
                'max_score': assignment.max_score,
                'time_limit': assignment.time_limit,
                'is_timed': assignment.is_timed
            },
            'validation': self._validate_for_publish(assignment),
            'student_view': self._generate_student_preview(assignment)
        }
        
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
                    'is_correct': opt.is_correct
                } for opt in q.options.all()] if q.question_type == 'mcq' else []
            } for q in questions]
        
        return Response(preview_data)
    
    @action(detail=True, methods=['post'], url_path='publish')
    def publish_assignment(self, request, pk=None):
        """Step 5: Final publish with validation"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status__in=['DRAFT', 'PREVIEW']
        )
        
        # Final validation
        validation_errors = self._validate_for_publish(assignment)
        if validation_errors['errors']:
            return Response({'errors': validation_errors['errors']}, status=400)
        
        # Publish assignment
        with transaction.atomic():
            assignment.status = 'PUBLISHED'
            assignment.published_at = timezone.now()
            assignment.save()
            
            # Auto-assign to students in class
            students = assignment.class_instance.students.all()
            for student in students:
                StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
        
        return Response({
            'id': assignment.id,
            'message': 'Assignment published successfully',
            'students_assigned': students.count(),
            'published_at': assignment.published_at
        })
    
    def _get_next_step(self, assignment_type, step=1):
        """Enhanced step flow with preview"""
        flows = {
            'HOMEWORK': ['type_selection', 'basic_info', 'settings', 'preview', 'publish'],
            'PROJECT': ['type_selection', 'basic_info', 'project_settings', 'preview', 'publish'],
            'QUIZ': ['type_selection', 'basic_info', 'quiz_settings', 'questions', 'preview', 'publish'],
            'EXAM': ['type_selection', 'basic_info', 'exam_settings', 'questions', 'preview', 'publish']
        }
        
        flow = flows.get(assignment_type, flows['HOMEWORK'])
        if step < len(flow):
            return flow[step]
        return 'publish'
    
    def _get_step_config(self, assignment_type, step=1):
        """Enhanced step configuration"""
        configs = {
            'HOMEWORK': {
                'settings': {
                    'fields': ['allow_file_submission', 'allow_text_submission', 'max_file_size', 'allowed_file_types'],
                    'description': 'Configure submission options for homework'
                }
            },
            'PROJECT': {
                'project_settings': {
                    'fields': ['allow_file_submission', 'max_file_size', 'allowed_file_types', 'rubric_criteria'],
                    'description': 'Configure project requirements and evaluation criteria'
                }
            },
            'QUIZ': {
                'quiz_settings': {
                    'fields': ['time_limit', 'auto_grade', 'show_results_immediately', 'question_randomization'],
                    'description': 'Configure quiz timing and grading options'
                },
                'questions': {
                    'requires_questions': True,
                    'question_types': ['mcq', 'short_answer'],
                    'description': 'Add questions to your quiz'
                }
            },
            'EXAM': {
                'exam_settings': {
                    'fields': ['time_limit', 'auto_grade', 'show_results_immediately', 'secure_mode'],
                    'description': 'Configure exam security and timing'
                },
                'questions': {
                    'requires_questions': True,
                    'question_types': ['mcq', 'short_answer'],
                    'description': 'Add questions to your exam'
                }
            }
        }
        
        return configs.get(assignment_type, {})
    
    def _validate_for_publish(self, assignment):
        """Comprehensive validation before publishing"""
        errors = []
        warnings = []
        
        # Basic validation
        if not assignment.title.strip():
            errors.append('Title is required')
        
        if not assignment.description.strip():
            errors.append('Description is required')
        
        if not assignment.instructions.strip():
            warnings.append('Instructions are recommended for clarity')
        
        if not assignment.class_subject:
            errors.append('Subject selection is required')
        
        # Type-specific validation
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            if not assignment.questions.exists():
                errors.append('Quiz/Exam must have at least one question')
            else:
                total_points = sum(q.points for q in assignment.questions.all())
                if total_points != assignment.max_score:
                    errors.append(f'Question points ({total_points}) must equal max score ({assignment.max_score})')
                
                # Check all MCQ questions have correct answers
                for question in assignment.questions.filter(question_type='mcq'):
                    if not question.options.filter(is_correct=True).exists():
                        errors.append(f'Question "{question.question_text[:30]}..." has no correct answer')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _generate_student_preview(self, assignment):
        """Generate how assignment will appear to students"""
        return {
            'title': assignment.title,
            'description': assignment.description,
            'instructions': assignment.instructions,
            'due_date': assignment.due_date.strftime('%B %d, %Y at %I:%M %p'),
            'points': f"{assignment.max_score} points",
            'time_limit': f"{assignment.time_limit} minutes" if assignment.time_limit else "No time limit",
            'submission_types': self._get_submission_types(assignment)
        }
    
    def _get_submission_types(self, assignment):
        """Get allowed submission types for preview"""
        types = []
        if assignment.allow_text_submission:
            types.append('Text Response')
        if assignment.allow_file_submission:
            types.append(f'File Upload (max {assignment.max_file_size}MB)')
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            types.append('Online Quiz')
        return types