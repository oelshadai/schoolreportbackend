"""
Assignment Workflow Engine API
Multi-step assignment creation with type-driven logic
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
from .serializers import AssignmentSerializer


class AssignmentWorkflowViewSet(viewsets.ViewSet):
    """Multi-step assignment creation workflow"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def create_draft(self, request):
        """Step 1: Create draft assignment with basic info"""
        data = request.data
        
        # Validate required fields
        required_fields = ['title', 'description', 'assignment_type', 'class_instance', 'due_date']
        for field in required_fields:
            if not data.get(field):
                return Response({'error': f'{field} is required'}, status=400)
        
        # Validate class access
        try:
            class_instance = Class.objects.get(
                id=data['class_instance'],
                class_teacher=request.user
            )
        except Class.DoesNotExist:
            return Response({'error': 'Invalid class or access denied'}, status=403)
        
        # Create draft assignment
        assignment = Assignment.objects.create(
            title=data['title'],
            description=data['description'],
            assignment_type=data['assignment_type'],
            class_instance=class_instance,
            created_by=request.user,
            due_date=data['due_date'],
            max_score=data.get('max_score', 10),
            status='DRAFT'
        )
        
        return Response({
            'id': assignment.id,
            'assignment_type': assignment.assignment_type,
            'workflow_state': self._get_workflow_state(assignment),
            'next_step': self._get_next_step(assignment.assignment_type)
        })
    
    @action(detail=True, methods=['patch'])
    def update_configuration(self, request, pk=None):
        """Step 2: Update type-specific configuration"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        data = request.data
        assignment_type = assignment.assignment_type
        
        # Type-specific configuration updates
        if assignment_type in ['QUIZ', 'EXAM']:
            if 'time_limit' in data:
                assignment.time_limit = data['time_limit']
            if 'auto_grade' in data:
                assignment.auto_grade = data['auto_grade']
            if 'show_results_immediately' in data:
                assignment.show_results_immediately = data['show_results_immediately']
        
        if assignment_type == 'PROJECT':
            if 'allow_file_submission' in data:
                assignment.allow_file_submission = data['allow_file_submission']
            if 'allow_text_submission' in data:
                assignment.allow_text_submission = data['allow_text_submission']
            if 'max_file_size' in data:
                assignment.max_file_size = data['max_file_size']
        
        # Update max_score if provided
        if 'max_score' in data:
            assignment.max_score = data['max_score']
        
        assignment.save()
        
        return Response({
            'id': assignment.id,
            'workflow_state': self._get_workflow_state(assignment),
            'next_step': self._get_next_step(assignment_type, current_step='config')
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
            return Response({'error': 'Questions only allowed for Quiz/Exam'}, status=400)
        
        data = request.data
        
        # Validate question data
        if not data.get('question_text'):
            return Response({'error': 'question_text is required'}, status=400)
        
        question_type = data.get('question_type', 'mcq')
        
        with transaction.atomic():
            # Create question
            question = Question.objects.create(
                assignment=assignment,
                question_text=data['question_text'],
                question_type=question_type,
                points=data.get('points', 1),
                order=assignment.questions.count() + 1
            )
            
            # Create MCQ options
            if question_type == 'mcq':
                options = data.get('options', [])
                if len(options) < 2:
                    return Response({'error': 'MCQ questions need at least 2 options'}, status=400)
                
                correct_count = sum(1 for opt in options if opt.get('is_correct'))
                if correct_count != 1:
                    return Response({'error': 'MCQ questions need exactly 1 correct option'}, status=400)
                
                for i, opt_data in enumerate(options):
                    QuestionOption.objects.create(
                        question=question,
                        option_text=opt_data['option_text'],
                        is_correct=opt_data.get('is_correct', False),
                        order=i
                    )
        
        # Calculate totals
        total_questions = assignment.questions.count()
        total_points = sum(q.points for q in assignment.questions.all())
        
        return Response({
            'question_id': question.id,
            'total_questions': total_questions,
            'total_points': total_points,
            'workflow_state': self._get_workflow_state(assignment)
        })
    
    @action(detail=True, methods=['delete'], url_path='questions/(?P<question_id>[^/.]+)')
    def remove_question(self, request, pk=None, question_id=None):
        """Remove question from assignment"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        question = get_object_or_404(
            Question,
            id=question_id,
            assignment=assignment
        )
        
        question.delete()
        
        # Reorder remaining questions
        remaining_questions = assignment.questions.order_by('order')
        for i, q in enumerate(remaining_questions, 1):
            q.order = i
            q.save()
        
        return Response({
            'total_questions': assignment.questions.count(),
            'total_points': sum(q.points for q in assignment.questions.all()),
            'workflow_state': self._get_workflow_state(assignment)
        })
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Step 4: Preview assignment before publishing"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        # Get questions with options
        questions = []
        for question in assignment.questions.order_by('order'):
            q_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points,
                'order': question.order
            }
            
            if question.question_type == 'mcq':
                q_data['options'] = [{
                    'id': opt.id,
                    'option_text': opt.option_text,
                    'is_correct': opt.is_correct,
                    'order': opt.order
                } for opt in question.options.order_by('order')]
            
            questions.append(q_data)
        
        # Validation status
        validation = self._validate_assignment(assignment)
        
        return Response({
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'assignment_type': assignment.assignment_type,
                'due_date': assignment.due_date,
                'time_limit': assignment.time_limit,
                'max_score': assignment.max_score,
                'auto_grade': assignment.auto_grade,
                'questions': questions
            },
            'validation': validation,
            'can_publish': validation['is_valid']
        })
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Step 5: Publish assignment"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user,
            status='DRAFT'
        )
        
        # Validate assignment
        validation = self._validate_assignment(assignment)
        if not validation['is_valid']:
            return Response({
                'error': 'Assignment validation failed',
                'validation_errors': validation['errors']
            }, status=400)
        
        with transaction.atomic():
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
            'id': assignment.id,
            'message': 'Assignment published successfully',
            'students_assigned': students.count(),
            'published_at': assignment.published_at
        })
    
    @action(detail=True, methods=['get'])
    def workflow_state(self, request, pk=None):
        """Get current workflow state"""
        assignment = get_object_or_404(
            Assignment,
            id=pk,
            created_by=request.user
        )
        
        return Response({
            'workflow_state': self._get_workflow_state(assignment),
            'next_step': self._get_next_step(assignment.assignment_type, 
                                           self._get_current_step(assignment))
        })
    
    def _get_workflow_state(self, assignment):
        """Get comprehensive workflow state"""
        state = {
            'assignment_type': assignment.assignment_type,
            'status': assignment.status,
            'has_basic_info': bool(assignment.title and assignment.description),
            'has_configuration': self._has_configuration(assignment),
            'has_questions': assignment.questions.exists(),
            'total_questions': assignment.questions.count(),
            'total_points': sum(q.points for q in assignment.questions.all()),
            'is_ready_to_publish': self._validate_assignment(assignment)['is_valid']
        }
        
        return state
    
    def _has_configuration(self, assignment):
        """Check if assignment has type-specific configuration"""
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            return assignment.time_limit is not None
        elif assignment.assignment_type == 'PROJECT':
            return True  # Project config is optional
        else:  # HOMEWORK
            return True  # No additional config needed
    
    def _get_current_step(self, assignment):
        """Determine current workflow step"""
        if not assignment.title:
            return 'basic_info'
        elif not self._has_configuration(assignment):
            return 'configuration'
        elif assignment.assignment_type in ['QUIZ', 'EXAM'] and not assignment.questions.exists():
            return 'questions'
        else:
            return 'review'
    
    def _get_next_step(self, assignment_type, current_step='basic_info'):
        """Determine next workflow step"""
        workflow_map = {
            'HOMEWORK': ['basic_info', 'review', 'publish'],
            'PROJECT': ['basic_info', 'configuration', 'review', 'publish'],
            'QUIZ': ['basic_info', 'configuration', 'questions', 'review', 'publish'],
            'EXAM': ['basic_info', 'configuration', 'questions', 'review', 'publish']
        }
        
        steps = workflow_map.get(assignment_type, workflow_map['HOMEWORK'])
        
        try:
            current_index = steps.index(current_step)
            if current_index + 1 < len(steps):
                return steps[current_index + 1]
        except ValueError:
            pass
        
        return 'review'
    
    def _validate_assignment(self, assignment):
        """Validate assignment for publishing"""
        errors = []
        
        # Basic validation
        if not assignment.title:
            errors.append('Title is required')
        if not assignment.description:
            errors.append('Description is required')
        if not assignment.due_date:
            errors.append('Due date is required')
        
        # Type-specific validation
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            if not assignment.questions.exists():
                errors.append('Quiz/Exam must have at least one question')
            else:
                total_points = sum(q.points for q in assignment.questions.all())
                if total_points != assignment.max_score:
                    errors.append(f'Question points ({total_points}) must equal max score ({assignment.max_score})')
                
                # Validate each question
                for question in assignment.questions.all():
                    if question.question_type == 'mcq':
                        if not question.options.exists():
                            errors.append(f'Question "{question.question_text[:30]}..." needs options')
                        elif not question.options.filter(is_correct=True).exists():
                            errors.append(f'Question "{question.question_text[:30]}..." needs a correct answer')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }