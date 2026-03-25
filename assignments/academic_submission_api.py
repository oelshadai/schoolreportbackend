"""
Academic Submission API with Backend Authority
All academic rules enforced server-side
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage

from .models import Assignment, StudentAssignment, QuizAttempt, QuizAnswer
from students.models import Student


class AcademicSubmissionViewSet(viewsets.ViewSet):
    """Backend authority for all academic submissions"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'], url_path='start')
    def start_assignment(self, request, pk=None):
        """Start assignment attempt with academic enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        # Get or create student assignment
        student_assignment, created = StudentAssignment.objects.get_or_create(
            assignment=assignment,
            student=student
        )
        
        try:
            student_assignment.start_attempt()
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        
        return Response({
            'assignment_id': assignment.id,
            'attempt_number': student_assignment.attempts_count,
            'max_attempts': assignment.max_attempts,
            'time_limit': assignment.time_limit if assignment.is_timed else None,
            'started_at': student_assignment.current_attempt_started_at,
            'assignment_type': assignment.assignment_type,
            'is_locked': student_assignment.is_locked
        })
    
    @action(detail=True, methods=['post'], url_path='submit-text')
    def submit_text(self, request, pk=None):
        """Submit text assignment with academic validation"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not started'}, status=400)
        
        # Academic enforcement
        if student_assignment.status != 'IN_PROGRESS':
            return Response({'error': 'Assignment not in progress'}, status=400)
        
        # Time limit enforcement
        if student_assignment.check_time_limit():\n            student_assignment.auto_submit_if_expired()\n            return Response({'error': 'Time limit exceeded'}, status=400)
        
        # Type-specific validation
        if assignment.assignment_type == 'PROJECT':\n            return Response({'error': 'Projects require file submission'}, status=400)
        
        if assignment.assignment_type in ['QUIZ', 'EXAM']:\n            return Response({'error': 'Use quiz submission endpoint'}, status=400)
        
        # Validate text submission
        submission_text = request.data.get('submission_text', '').strip()
        if not submission_text:\n            return Response({'error': 'Text submission cannot be empty'}, status=400)
        
        # Submit with academic validation
        try:
            with transaction.atomic():
                student_assignment.submission_text = submission_text
                student_assignment.submit()
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        
        return Response({
            'message': 'Assignment submitted successfully',
            'submitted_at': student_assignment.submitted_at,
            'attempt_number': student_assignment.attempts_count
        })
    
    @action(detail=True, methods=['post'], url_path='submit-file')
    def submit_file(self, request, pk=None):
        """Submit file assignment with academic validation"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not started'}, status=400)
        
        # Academic enforcement
        if student_assignment.status != 'IN_PROGRESS':
            return Response({'error': 'Assignment not in progress'}, status=400)
        
        # Time limit enforcement
        if student_assignment.check_time_limit():
            student_assignment.auto_submit_if_expired()
            return Response({'error': 'Time limit exceeded'}, status=400)
        
        # File validation
        if 'submission_file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['submission_file']
        
        # Type-specific file validation
        max_size = self._get_max_file_size(assignment.assignment_type)
        if file.size > max_size:
            return Response({
                'error': f'File size exceeds {max_size // (1024*1024)}MB limit'
            }, status=400)
        
        # File type validation
        allowed_types = assignment.allowed_file_types.split(',')
        file_ext = file.name.split('.')[-1].lower()
        if file_ext not in [t.strip().lower() for t in allowed_types]:
            return Response({
                'error': f'File type .{file_ext} not allowed. Allowed: {assignment.allowed_file_types}'
            }, status=400)
        
        # Submit with academic validation
        try:
            with transaction.atomic():
                student_assignment.submission_file = file
                student_assignment.submit({'file': file})
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        
        return Response({
            'message': 'File submitted successfully',
            'submitted_at': student_assignment.submitted_at,
            'filename': file.name,
            'attempt_number': student_assignment.attempts_count
        })
    
    @action(detail=True, methods=['post'], url_path='submit-quiz')
    def submit_quiz(self, request, pk=None):
        """Submit quiz/exam with academic enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        if assignment.assignment_type not in ['QUIZ', 'EXAM']:
            return Response({'error': 'Not a quiz or exam'}, status=400)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Assignment not started'}, status=400)
        
        # Academic enforcement
        if student_assignment.status != 'IN_PROGRESS':
            return Response({'error': 'Assignment not in progress'}, status=400)
        
        # Time limit enforcement (critical for exams)
        if student_assignment.check_time_limit():
            if assignment.assignment_type == 'EXAM':
                # Auto-submit expired exam
                student_assignment.auto_submit_if_expired()
                return Response({
                    'message': 'Exam auto-submitted due to time limit',
                    'submitted_at': student_assignment.submitted_at
                })
            else:
                return Response({'error': 'Time limit exceeded'}, status=400)
        
        answers = request.data.get('answers', {})
        if not answers:
            return Response({'error': 'No answers provided'}, status=400)
        
        # Validate all questions answered
        required_questions = assignment.questions.filter(is_required=True)
        for question in required_questions:
            if str(question.id) not in answers:
                return Response({
                    'error': f'Question {question.order} is required'
                }, status=400)
        
        # Submit quiz with academic validation
        try:
            with transaction.atomic():
                # Create quiz attempt
                quiz_attempt = QuizAttempt.objects.create(
                    assignment=assignment,
                    student=student,
                    started_at=student_assignment.current_attempt_started_at
                )
                
                # Save answers
                for question_id, answer_data in answers.items():
                    question = assignment.questions.get(id=question_id)
                    quiz_answer = QuizAnswer.objects.create(
                        attempt=quiz_attempt,
                        question=question
                    )
                    
                    if question.question_type == 'mcq':
                        option_id = answer_data
                        quiz_answer.selected_option_id = option_id
                    else:
                        quiz_answer.answer_text = answer_data
                    
                    quiz_answer.check_answer()
                    quiz_answer.save()
                
                # Calculate score and submit
                quiz_attempt.calculate_score()
                student_assignment.score = quiz_attempt.score
                student_assignment.submit({'answers': answers})
                
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        
        return Response({
            'message': 'Quiz submitted successfully',
            'score': float(student_assignment.score) if student_assignment.score else 0,
            'submitted_at': student_assignment.submitted_at,
            'attempt_number': student_assignment.attempts_count
        })
    
    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, pk=None):
        """Get assignment status with time enforcement"""
        assignment = get_object_or_404(Assignment, id=pk, status='PUBLISHED')
        student = get_object_or_404(Student, user=request.user)
        
        try:
            student_assignment = StudentAssignment.objects.get(
                assignment=assignment,
                student=student
            )
        except StudentAssignment.DoesNotExist:
            return Response({
                'status': 'NOT_STARTED',
                'can_start': True,
                'attempts_remaining': assignment.max_attempts
            })
        
        # Check and handle time expiration
        student_assignment.auto_submit_if_expired()
        
        # Calculate time remaining
        time_remaining = None
        if (student_assignment.status == 'IN_PROGRESS' and 
            assignment.is_timed and 
            student_assignment.current_attempt_started_at):
            
            elapsed = timezone.now() - student_assignment.current_attempt_started_at
            remaining_seconds = (assignment.time_limit * 60) - elapsed.total_seconds()
            time_remaining = max(0, int(remaining_seconds))
        
        can_start, message = student_assignment.can_start_attempt()
        
        return Response({
            'status': student_assignment.status,
            'attempts_made': student_assignment.attempts_count,
            'max_attempts': assignment.max_attempts,
            'can_start': can_start,
            'message': message,
            'time_remaining': time_remaining,
            'is_locked': student_assignment.is_locked,
            'submitted_at': student_assignment.submitted_at,
            'score': float(student_assignment.score) if student_assignment.score else None
        })
    
    def _get_max_file_size(self, assignment_type):
        """Get max file size based on assignment type"""
        sizes = {
            'PROJECT': 50 * 1024 * 1024,  # 50MB
            'HOMEWORK': 10 * 1024 * 1024,  # 10MB
            'EXERCISE': 5 * 1024 * 1024,   # 5MB
        }
        return sizes.get(assignment_type, 10 * 1024 * 1024)