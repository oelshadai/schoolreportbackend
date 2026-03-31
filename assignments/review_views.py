"""
Assignment Review Views
Allows students to review their submitted assignments with correct answers and feedback
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Assignment, StudentAssignment, QuizAttempt, QuizAnswer, Question, QuestionOption
from students.models import Student


class AssignmentReviewViewSet(viewsets.ViewSet):
    """Viewset for students to review their submitted assignments"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='my-submissions')
    def my_submissions(self, request):
        """Get all student's submitted assignments available for review"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        # Get all submitted/graded assignments
        student_assignments = StudentAssignment.objects.filter(
            student=student,
            status__in=['SUBMITTED', 'GRADED']
        ).select_related('assignment').order_by('-submitted_at')
        
        submissions = []
        for sa in student_assignments:
            assignment = sa.assignment
            
            # Check if review is allowed (assignment is graded or allows immediate review)
            can_review = self._can_student_review_assignment(assignment, sa)
            
            submissions.append({
                'id': sa.id,
                'assignment': {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'assignment_type': assignment.assignment_type,
                    'max_score': assignment.max_score,
                    'due_date': assignment.due_date
                },
                'status': sa.status,
                'score': sa.score,
                'submitted_at': sa.submitted_at,
                'graded_at': sa.graded_at,
                'teacher_feedback': sa.teacher_feedback,
                'can_review': can_review,
                'attempts_count': sa.attempts_count
            })
        
        return Response(submissions)
    
    @action(detail=True, methods=['get'], url_path='review')
    def review_submission(self, request, pk=None):
        """Get detailed review of a specific submission"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        # Get the student assignment
        try:
            student_assignment = StudentAssignment.objects.get(
                id=pk,
                student=student,
                status__in=['SUBMITTED', 'GRADED']
            )
        except StudentAssignment.DoesNotExist:
            return Response({'error': 'Submission not found or not available for review'}, status=404)
        
        assignment = student_assignment.assignment
        
        # Check if review is allowed
        can_review = self._can_student_review_assignment(assignment, student_assignment)
        
        if not can_review:
            return Response({'error': 'Review not available yet or disabled by teacher.'}, status=403)
        
        review_data = {
            'submission': {
                'id': student_assignment.id,
                'status': student_assignment.status,
                'score': student_assignment.score,
                'submitted_at': student_assignment.submitted_at,
                'graded_at': student_assignment.graded_at,
                'teacher_feedback': student_assignment.teacher_feedback,
                'attempts_count': student_assignment.attempts_count
            },
            'assignment': {
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'assignment_type': assignment.assignment_type,
                'max_score': assignment.max_score,
                'instructions': assignment.instructions
            }
        }
        
        if assignment.assignment_type in ['QUIZ', 'EXAM']:
            # Get quiz review data
            review_data.update(self._get_quiz_review_data(student_assignment, assignment, student))
        else:
            # Get regular assignment review data
            review_data.update(self._get_assignment_review_data(student_assignment))
        
        return Response(review_data)
    
    def _get_quiz_review_data(self, student_assignment, assignment, student):
        """Get quiz-specific review data with correct answers"""
        try:
            quiz_attempt = QuizAttempt.objects.get(
                assignment=assignment,
                student=student
            )
        except QuizAttempt.DoesNotExist:
            return {'questions': [], 'quiz_summary': {}}
        
        # Get all questions and student answers
        questions = Question.objects.filter(
            assignment=assignment
        ).prefetch_related('options').order_by('order', 'id')
        
        student_answers = {
            qa.question_id: qa for qa in QuizAnswer.objects.filter(
                attempt=quiz_attempt
            ).select_related('selected_option', 'question')
        }
        
        questions_review = []
        total_questions = 0
        correct_answers = 0
        total_points = 0
        earned_points = 0
        
        for question in questions:
            total_questions += 1
            total_points += question.points
            
            student_answer = student_answers.get(question.id)
            
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points,
                'order': question.order,
                'explanation': question.explanation
            }
            
            if question.question_type == 'mcq':
                # Multiple choice question review
                options = []
                correct_option_id = None
                
                for option in question.options.all().order_by('order', 'id'):
                    options.append({
                        'id': option.id,
                        'option_text': option.option_text,
                        'is_correct': option.is_correct,
                        'order': option.order
                    })
                    if option.is_correct:
                        correct_option_id = option.id
                
                question_data['options'] = options
                question_data['correct_option_id'] = correct_option_id
                
                if student_answer:
                    question_data['student_selected_option_id'] = student_answer.selected_option.id if student_answer.selected_option else None
                    question_data['is_correct'] = student_answer.is_correct
                    question_data['points_earned'] = student_answer.points_earned
                    
                    if student_answer.is_correct:
                        correct_answers += 1
                    earned_points += student_answer.points_earned
                else:
                    question_data['student_selected_option_id'] = None
                    question_data['is_correct'] = False
                    question_data['points_earned'] = 0
            
            elif question.question_type == 'short_answer':
                # Short answer question review
                question_data['expected_answer'] = question.expected_answer
                question_data['case_sensitive'] = question.case_sensitive
                
                if student_answer:
                    question_data['student_answer'] = student_answer.answer_text
                    question_data['is_correct'] = student_answer.is_correct
                    question_data['points_earned'] = student_answer.points_earned
                    question_data['teacher_comment'] = student_answer.teacher_comment
                    
                    if student_answer.is_correct:
                        correct_answers += 1
                    earned_points += student_answer.points_earned
                else:
                    question_data['student_answer'] = ''
                    question_data['is_correct'] = False
                    question_data['points_earned'] = 0
                    question_data['teacher_comment'] = ''
            
            elif question.question_type == 'project':
                # Project question review
                question_data['allowed_file_types'] = question.allowed_file_types
                question_data['max_file_size'] = question.max_file_size
                question_data['max_files'] = question.max_files
                
                if student_answer:
                    question_data['student_answer'] = student_answer.answer_text
                    question_data['points_earned'] = student_answer.points_earned
                    question_data['teacher_comment'] = student_answer.teacher_comment
                    question_data['is_correct'] = student_answer.is_correct
                    
                    # Get uploaded files
                    uploaded_files = []
                    for file_obj in student_answer.uploaded_files.all():
                        uploaded_files.append({
                            'id': file_obj.id,
                            'filename': file_obj.original_filename,
                            'url': file_obj.file.url,
                            'size': file_obj.file_size,
                            'uploaded_at': file_obj.uploaded_at
                        })
                    question_data['uploaded_files'] = uploaded_files
                    
                    if student_answer.points_earned > 0:
                        correct_answers += 1
                    earned_points += student_answer.points_earned
                else:
                    question_data['student_answer'] = ''
                    question_data['points_earned'] = 0
                    question_data['teacher_comment'] = ''
                    question_data['uploaded_files'] = []
                    question_data['is_correct'] = False
            
            questions_review.append(question_data)
        
        quiz_summary = {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'wrong_answers': total_questions - correct_answers,
            'accuracy_percentage': (correct_answers / total_questions * 100) if total_questions > 0 else 0,
            'total_points': total_points,
            'earned_points': earned_points,
            'score_percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'final_score': quiz_attempt.score,
            'time_taken': quiz_attempt.time_taken,
            'submitted_at': quiz_attempt.submitted_at
        }
        
        return {
            'questions': questions_review,
            'quiz_summary': quiz_summary
        }
    
    def _get_assignment_review_data(self, student_assignment):
        """Get regular assignment review data"""
        return {
            'submission_content': {
                'text_content': student_assignment.submission_text,
                'file_url': student_assignment.submission_file.url if student_assignment.submission_file else None,
                'file_name': student_assignment.submission_file.name if student_assignment.submission_file else None
            },
            'grading': {
                'score': student_assignment.score,
                'max_score': student_assignment.assignment.max_score,
                'percentage': (student_assignment.score / student_assignment.assignment.max_score * 100) if student_assignment.score and student_assignment.assignment.max_score else 0,
                'teacher_feedback': student_assignment.teacher_feedback,
                'graded_at': student_assignment.graded_at
            }
        }
    
    @action(detail=False, methods=['get'], url_path='quiz-statistics')
    def quiz_statistics(self, request):
        """Get overall quiz statistics for the student"""
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)
        
        # Get all quiz attempts
        quiz_attempts = QuizAttempt.objects.filter(
            student=student,
            status__in=['SUBMITTED', 'GRADED']
        ).select_related('assignment')
        
        if not quiz_attempts.exists():
            return Response({
                'total_quizzes': 0,
                'average_score': 0,
                'best_score': 0,
                'recent_quizzes': []
            })
        
        total_score = sum(attempt.score or 0 for attempt in quiz_attempts)
        average_score = total_score / len(quiz_attempts)
        best_score = max(attempt.score or 0 for attempt in quiz_attempts)
        
        recent_quizzes = []
        for attempt in quiz_attempts.order_by('-submitted_at')[:5]:
            recent_quizzes.append({
                'assignment_title': attempt.assignment.title,
                'score': attempt.score,
                'max_score': attempt.assignment.max_score,
                'percentage': (attempt.score / attempt.assignment.max_score * 100) if attempt.score and attempt.assignment.max_score else 0,
                'submitted_at': attempt.submitted_at
            })
        
        return Response({
            'total_quizzes': len(quiz_attempts),
            'average_score': round(average_score, 2),
            'best_score': best_score,
            'recent_quizzes': recent_quizzes
        })
    
    def _can_student_review_assignment(self, assignment, student_assignment):
        """Check if a student can review their assignment based on teacher settings"""
        if not assignment.allow_review:
            return False
        
        if assignment.review_available_after == 'NEVER':
            return False
        elif assignment.review_available_after == 'IMMEDIATE':
            return student_assignment.status in ['SUBMITTED', 'GRADED']
        elif assignment.review_available_after == 'GRADED':
            return student_assignment.status == 'GRADED'
        elif assignment.review_available_after == 'MANUAL':
            return assignment.review_enabled_at is not None and student_assignment.status in ['SUBMITTED', 'GRADED']
        
        return False