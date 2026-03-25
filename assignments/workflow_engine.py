"""
VClass Workflow Engine - Backend Core
Handles multi-step assignment creation with type-driven logic
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from schools.models import Class
from .models import Assignment, Question, QuestionOption


class WorkflowEngineViewSet(viewsets.ViewSet):
    """Multi-step assignment creation workflow engine"""
    permission_classes = [IsAuthenticated]
    
    # Workflow step definitions
    WORKFLOW_STEPS = {
        'HOMEWORK': ['basic_info', 'settings', 'review'],
        'PROJECT': ['basic_info', 'project_settings', 'review'],
        'QUIZ': ['basic_info', 'quiz_settings', 'questions', 'review'],
        'EXAM': ['basic_info', 'exam_settings', 'questions', 'review']
    }
    
    @action(detail=False, methods=['post'])
    def start_workflow(self, request):
        """Step 1: Create draft assignment with basic info"""
        data = request.data
        
        # Validate required fields
        required = ['title', 'description', 'assignment_type', 'class_instance', 'due_date', 'max_score']
        for field in required:
            if not data.get(field):
                return Response({'error': f'{field} required'}, status=400)
        
        # Create draft assignment
        assignment = Assignment.objects.create(
            title=data['title'],
            description=data['description'],
            assignment_type=data['assignment_type'],
            class_instance_id=data['class_instance'],
            created_by=request.user,
            due_date=data['due_date'],
            max_score=data['max_score'],
            status='DRAFT'
        )
        
        return Response({
            'workflow_id': assignment.id,
            'assignment_type': assignment.assignment_type,
            'next_step': self._get_next_step(assignment.assignment_type),
            'steps_remaining': self._get_steps_remaining(assignment.assignment_type)
        })
    
    @action(detail=True, methods=['patch'])
    def configure_assignment(self, request, pk=None):
        """Step 2: Type-specific configuration"""
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
            assignment.is_timed = bool(data.get('time_limit'))
            assignment.auto_grade = data.get('auto_grade', True)
            assignment.show_results_immediately = data.get('show_results_immediately', True)
        
        elif assignment_type == 'PROJECT':
            assignment.allow_file_submission = data.get('allow_file_submission', True)
            assignment.allow_text_submission = data.get('allow_text_submission', True)
            assignment.max_file_size = data.get('max_file_size', 10)
            assignment.allowed_file_types = data.get('allowed_file_types', 'pdf,doc,docx,jpg,png')
        
        assignment.save()
        
        return Response({
            'workflow_id': assignment.id,
            'next_step': self._get_next_step(assignment_type, current_step=2),
            'configuration_saved': True
        })
    
    @action(detail=True, methods=['post'])
    def add_question(self, request, pk=None):
        """Step 3: Add questions (Quiz/Exam only)"""
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
            
            # Add MCQ options
            if data['question_type'] == 'mcq':
                for opt_data in data.get('options', []):
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
            'can_publish': total_points == assignment.max_score
        })
    
    @action(detail=True, methods=['get'])
    def workflow_status(self, request, pk=None):
        """Get current workflow status"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user
        )
        
        status_data = {
            'workflow_id': assignment.id,
            'assignment_type': assignment.assignment_type,
            'status': assignment.status,
            'current_step': self._get_current_step(assignment),
            'can_publish': self._can_publish(assignment),
            'validation_errors': self._validate_assignment(assignment)
        }
        
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            status_data['questions_count'] = assignment.questions.count()
            status_data['total_points'] = sum(q.points for q in assignment.questions.all())
        
        return Response(status_data)
    
    @action(detail=True, methods=['post'])
    def publish_assignment(self, request, pk=None):
        """Final Step: Publish assignment"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        # Validate before publishing
        errors = self._validate_assignment(assignment)
        if errors:
            return Response({'errors': errors}, status=400)
        
        # Publish assignment
        assignment.status = 'PUBLISHED'
        assignment.published_at = timezone.now()
        assignment.save()
        
        # Auto-assign to students
        from .models import StudentAssignment
        students = assignment.class_instance.students.all()
        for student in students:
            StudentAssignment.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )
        
        return Response({
            'workflow_id': assignment.id,
            'status': 'PUBLISHED',
            'students_assigned': students.count(),
            'message': 'Assignment published successfully'
        })
    
    def _get_next_step(self, assignment_type, current_step=1):
        """Determine next step based on type and current step"""
        if current_step == 1:
            if assignment_type == 'HOMEWORK':
                return 'review'
            elif assignment_type == 'PROJECT':
                return 'project_config'
            elif assignment_type in ['QUIZ', 'EXAM']:
                return 'quiz_config'
        elif current_step == 2:
            if assignment_type in ['QUIZ', 'EXAM']:
                return 'questions'
            else:
                return 'review'
        return 'review'
    
    def _get_steps_remaining(self, assignment_type):
        """Get total steps for assignment type"""
        if assignment_type == 'HOMEWORK':
            return ['basic_info', 'review']
        elif assignment_type == 'PROJECT':
            return ['basic_info', 'project_config', 'review']
        elif assignment_type in ['QUIZ', 'EXAM']:
            return ['basic_info', 'quiz_config', 'questions', 'review']
        return ['basic_info', 'review']
    
    def _get_current_step(self, assignment):
        """Determine current step based on assignment state"""
        if assignment.status == 'PUBLISHED':
            return 'published'
        
        assignment_type = assignment.assignment_type
        
        if assignment_type in ['QUIZ', 'EXAM']:
            if assignment.questions.exists():
                return 'review'
            elif assignment.time_limit is not None:
                return 'questions'
            else:
                return 'quiz_config'
        elif assignment_type == 'PROJECT':
            if hasattr(assignment, 'allow_file_submission'):
                return 'review'
            else:
                return 'project_config'
        else:  # HOMEWORK
            return 'review'
    
    def _can_publish(self, assignment):
        """Check if assignment can be published"""
        return len(self._validate_assignment(assignment)) == 0
    
    @action(detail=True, methods=['post'])
    def validate_step(self, request, pk=None):
        """Validate current workflow step"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        step = request.data.get('step')
        data = request.data.get('data', {})
        
        validation_result = self._validate_step(assignment, step, data)
        
        return Response({
            'step': step,
            'valid': validation_result['valid'],
            'errors': validation_result['errors'],
            'next_step': validation_result.get('next_step')
        })
    
    def _validate_step(self, assignment, step, data):
        """Validate specific workflow step"""
        errors = []
        assignment_type = assignment.assignment_type
        
        if step == 'basic_info':
            if not data.get('title', '').strip():
                errors.append('Title is required')
            if not data.get('description', '').strip():
                errors.append('Description is required')
            if not data.get('due_date'):
                errors.append('Due date is required')
            if not data.get('max_score') or int(data.get('max_score', 0)) <= 0:
                errors.append('Max score must be greater than 0')
        
        elif step in ['quiz_settings', 'exam_settings']:
            if data.get('is_timed') and not data.get('time_limit'):
                errors.append('Time limit required for timed assignments')
        
        elif step == 'questions':
            if assignment_type in ['QUIZ', 'EXAM']:
                questions_count = assignment.questions.count()
                if questions_count == 0:
                    errors.append('At least one question is required')
                
                total_points = sum(q.points for q in assignment.questions.all())
                if total_points != assignment.max_score:
                    errors.append(f'Question points ({total_points}) must equal max score ({assignment.max_score})')
        
        # Determine next step
        next_step = self._get_next_step_after_validation(assignment_type, step, len(errors) == 0)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'next_step': next_step
        }
    
    def _get_next_step_after_validation(self, assignment_type, current_step, is_valid):
        """Get next step after validation"""
        if not is_valid:
            return current_step  # Stay on current step if invalid
        
        steps = self.WORKFLOW_STEPS.get(assignment_type, [])
        try:
            current_index = steps.index(current_step)
            if current_index < len(steps) - 1:
                return steps[current_index + 1]
        except ValueError:
            pass
        
        return 'review'  # Default to review step
    
    def _validate_assignment(self, assignment):
        """Validate assignment before publishing"""
        errors = []
        
        # Basic validation
        if not assignment.title.strip():
            errors.append('Title is required')
        
        if not assignment.due_date:
            errors.append('Due date is required')
        
        # Type-specific validation
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            if not assignment.questions.exists():
                errors.append('Quiz/Exam must have questions')
            else:
                total_points = sum(q.points for q in assignment.questions.all())
                if total_points != assignment.max_score:
                    errors.append(f'Question points ({total_points}) must equal max score ({assignment.max_score})')
        
        return errors