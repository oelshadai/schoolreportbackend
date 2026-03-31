"""
Assignment Grading Views
Handles manual grading of assignments, especially short answers and project submissions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.db import models
from django.utils import timezone

from .models import Assignment, StudentAssignment, QuizAnswer, QuizAttempt
from .serializers import AssignmentSerializer, StudentAssignmentSerializer
from students.models import Student


class GradingViewSet(viewsets.ViewSet):
    """Viewset for handling assignment grading"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='pending-grading')
    def pending_grading(self, request):
        """Get assignments that have submissions needing manual grading"""
        user = request.user
        
        # Get assignments created by this teacher or for classes they teach
        from schools.models import ClassSubject
        
        teacher_subjects = ClassSubject.objects.filter(
            teacher=user
        ).values_list('id', flat=True)
        
        # All published assignments for this teacher
        base_assignments = Assignment.objects.filter(
            Q(created_by=user) |
            Q(class_subject__in=teacher_subjects) |
            Q(class_instance__class_teacher=user)
        ).filter(
            status='PUBLISHED'
        )

        # Homework/project pending by StudentAssignment SUBMITTED
        pending_hw_assignments = StudentAssignment.objects.filter(
            assignment__in=base_assignments,
            status='SUBMITTED',
            assignment__assignment_type__in=['HOMEWORK', 'PROJECT']
        ).values_list('assignment_id', flat=True).distinct()

        # Quiz/exam pending by short_answer/project quiz answers not yet graded OR submitted attempts
        quiz_assignments = base_assignments.filter(assignment_type__in=['QUIZ', 'EXAM'])

        pending_quiz_attempts = QuizAttempt.objects.filter(
            assignment__in=quiz_assignments,
            status='SUBMITTED'
        ).values_list('assignment_id', flat=True).distinct()

        pending_quiz_ungraded = QuizAnswer.objects.filter(
            attempt__assignment__in=quiz_assignments,
            question__question_type__in=['short_answer', 'project'],
            is_correct__isnull=True
        ).values_list('attempt__assignment_id', flat=True).distinct()

        pending_assignment_ids = set(list(pending_hw_assignments)) | set(list(pending_quiz_attempts)) | set(list(pending_quiz_ungraded))

        assignments = base_assignments.filter(id__in=pending_assignment_ids)

        assignment_data = []
        for assignment in assignments:
            # Count submissions needing grading
            if assignment.assignment_type in ['HOMEWORK', 'PROJECT']:
                pending_count = StudentAssignment.objects.filter(
                    assignment=assignment,
                    status='SUBMITTED'
                ).count()
            else:
                pending_count = QuizAnswer.objects.filter(
                    attempt__assignment=assignment,
                    question__question_type__in=['short_answer', 'project'],
                    is_correct__isnull=True
                ).values('attempt').distinct().count()

            if pending_count > 0:
                assignment_data.append({
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'assignment_type': assignment.assignment_type,
                    'due_date': assignment.due_date,
                    'max_score': assignment.max_score,
                    'subject': {
                        'id': assignment.class_subject.subject.id if assignment.class_subject else None,
                        'name': assignment.class_subject.subject.name if assignment.class_subject else 'General'
                    },
                    'class_instance': {
                        'id': assignment.class_instance.id,
                        'name': str(assignment.class_instance)
                    },
                    'pending_submissions': pending_count,
                    'is_auto_graded': assignment.auto_grade and assignment.assignment_type in ['QUIZ', 'EXAM']
                })
        
        assignment_data = []
        for assignment in assignments:
            # Count submissions needing grading
            if assignment.assignment_type in ['HOMEWORK', 'PROJECT']:
                # All submitted homework/projects need manual grading
                pending_count = StudentAssignment.objects.filter(
                    assignment=assignment,
                    status='SUBMITTED'
                ).count()
            else:
                # For quizzes/exams, count those with short answer or project questions
                pending_count = QuizAnswer.objects.filter(
                    attempt__assignment=assignment,
                    question__question_type__in=['short_answer', 'project'],
                    is_correct__isnull=True  # Not yet graded
                ).values('attempt').distinct().count()
            
            if pending_count > 0:
                assignment_data.append({
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'assignment_type': assignment.assignment_type,
                    'due_date': assignment.due_date,
                    'max_score': assignment.max_score,
                    'subject': {
                        'id': assignment.class_subject.subject.id if assignment.class_subject else None,
                        'name': assignment.class_subject.subject.name if assignment.class_subject else 'General'
                    },
                    'class_instance': {
                        'id': assignment.class_instance.id,
                        'name': str(assignment.class_instance)
                    },
                    'pending_submissions': pending_count,
                    'is_auto_graded': assignment.auto_grade and assignment.assignment_type in ['QUIZ', 'EXAM']
                })
        
        return Response({'results': assignment_data})
    
    @action(detail=True, methods=['get'], url_path='submissions')
    def get_submissions(self, request, pk=None):
        """Get submissions for an assignment that need grading"""
        assignment = get_object_or_404(Assignment, id=pk)
        
        # Verify teacher has access
        user = request.user
        has_access = (
            assignment.created_by == user or
            assignment.class_instance.class_teacher == user or
            (assignment.class_subject and assignment.class_subject.teacher == user)
        )
        
        if not has_access:
            return Response({'error': 'Access denied'}, status=403)
        
        submissions = []
        
        if assignment.assignment_type in ['HOMEWORK', 'PROJECT']:
            # Get regular submissions
            student_assignments = StudentAssignment.objects.filter(
                assignment=assignment,
                status__in=['SUBMITTED', 'GRADED']
            ).select_related('student').order_by('student__first_name')
            
            for sa in student_assignments:
                submissions.append({
                    'id': sa.id,
                    'student': {
                        'id': sa.student.id,
                        'name': sa.student.get_full_name(),
                        'student_id': sa.student.student_id
                    },
                    'assignment': {
                        'id': assignment.id,
                        'title': assignment.title,
                        'max_score': assignment.max_score
                    },
                    'submitted_at': sa.submitted_at,
                    'file_url': sa.submission_file.url if sa.submission_file else None,
                    'text_content': sa.submission_text,
                    'score': sa.score,
                    'feedback': sa.teacher_feedback,
                    'status': 'graded' if sa.status == 'GRADED' else 'submitted',
                    'is_auto_graded': False
                })
        
        elif assignment.assignment_type in ['QUIZ', 'EXAM']:
            # Get quiz attempts with short answer or project questions
            quiz_attempts = QuizAttempt.objects.filter(
                assignment=assignment,
                status__in=['SUBMITTED', 'GRADED']
            ).select_related('student').order_by('student__first_name')
            
            for attempt in quiz_attempts:
                # Check if this attempt has UNGRADED questions needing manual grading
                ungraded_manual_questions = QuizAnswer.objects.filter(
                    attempt=attempt,
                    question__question_type__in=['short_answer', 'project'],
                    is_correct__isnull=True  # Not yet graded
                )
                
                if ungraded_manual_questions.exists():
                    # Get text content from short answer questions
                    text_answers = []
                    for qa in ungraded_manual_questions:
                        if qa.question.question_type == 'short_answer':
                            text_answers.append(f"Q: {qa.question.question_text}\nA: {qa.answer_text}")
                        elif qa.question.question_type == 'project':
                            text_answers.append(f"Q: {qa.question.question_text}\nFiles: {len(qa.uploaded_files.all())} uploaded")
                    
                    submissions.append({
                        'id': f"quiz_{attempt.id}",
                        'student': {
                            'id': attempt.student.id,
                            'name': attempt.student.get_full_name(),
                            'student_id': attempt.student.student_id
                        },
                        'assignment': {
                            'id': assignment.id,
                            'title': assignment.title,
                            'max_score': assignment.max_score
                        },
                        'submitted_at': attempt.submitted_at,
                        'file_url': None,  # Quiz files handled separately
                        'text_content': '\n\n'.join(text_answers),
                        'score': attempt.score,
                        'feedback': '',  # Quiz feedback handled per question
                        'status': 'submitted',  # Always show as needing grading
                        'is_auto_graded': False,
                        'quiz_attempt_id': attempt.id
                    })
        
        return Response({'results': submissions})
    
    @action(detail=False, methods=['patch'], url_path='grade-submission')
    def grade_submission(self, request):
        """Grade a submission"""
        submission_id = request.data.get('submission_id')
        score = request.data.get('score')
        feedback = request.data.get('feedback', '')
        
        if not submission_id or score is None:
            return Response({'error': 'submission_id and score are required'}, status=400)
        
        try:
            if submission_id.startswith('quiz_'):
                # Handle quiz grading
                attempt_id = submission_id.replace('quiz_', '')
                attempt = get_object_or_404(QuizAttempt, id=attempt_id)
                
                # Update attempt score and status
                attempt.score = float(score)
                attempt.status = 'GRADED'
                attempt.save()
                
                # Update corresponding StudentAssignment
                try:
                    student_assignment = StudentAssignment.objects.get(
                        assignment=attempt.assignment,
                        student=attempt.student
                    )
                    student_assignment.score = float(score)
                    student_assignment.status = 'GRADED'
                    student_assignment.teacher_feedback = feedback
                    student_assignment.graded_at = timezone.now()
                    student_assignment.save()
                except StudentAssignment.DoesNotExist:
                    pass
                
                return Response({
                    'message': 'Quiz graded successfully',
                    'score': float(score)
                })
            
            else:
                # Handle regular assignment grading
                student_assignment = get_object_or_404(StudentAssignment, id=submission_id)
                
                student_assignment.score = float(score)
                student_assignment.teacher_feedback = feedback
                student_assignment.status = 'GRADED'
                student_assignment.graded_at = timezone.now()
                student_assignment.save()
                
                return Response({
                    'message': 'Assignment graded successfully',
                    'score': float(score)
                })
        
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['get'], url_path='quiz-details')
    def quiz_details(self, request, pk=None):
        """Get detailed quiz answers for grading"""
        try:
            attempt_id = pk.replace('quiz_', '') if pk.startswith('quiz_') else pk
            attempt = get_object_or_404(QuizAttempt, id=attempt_id)
            
            # Get all answers for this attempt
            answers = QuizAnswer.objects.filter(
                attempt=attempt
            ).select_related('question').prefetch_related('uploaded_files')
            
            answer_data = []
            for answer in answers:
                answer_info = {
                    'id': answer.id,
                    'question': {
                        'id': answer.question.id,
                        'text': answer.question.question_text,
                        'type': answer.question.question_type,
                        'points': answer.question.points
                    },
                    'answer_text': answer.answer_text,
                    'selected_option': answer.selected_option.option_text if answer.selected_option else None,
                    'is_correct': answer.is_correct,
                    'points_earned': answer.points_earned,
                    'teacher_comment': answer.teacher_comment,
                    'files': []
                }
                
                # Add uploaded files for project questions
                if answer.question.question_type == 'project':
                    for file_obj in answer.uploaded_files.all():
                        answer_info['files'].append({
                            'id': file_obj.id,
                            'filename': file_obj.original_filename,
                            'url': file_obj.file.url,
                            'size': file_obj.file_size
                        })
                
                answer_data.append(answer_info)
            
            return Response({
                'attempt': {
                    'id': attempt.id,
                    'student': {
                        'id': attempt.student.id,
                        'name': attempt.student.get_full_name(),
                        'student_id': attempt.student.student_id
                    },
                    'assignment': {
                        'id': attempt.assignment.id,
                        'title': attempt.assignment.title,
                        'max_score': attempt.assignment.max_score
                    },
                    'score': attempt.score,
                    'status': attempt.status,
                    'submitted_at': attempt.submitted_at
                },
                'answers': answer_data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=False, methods=['patch'], url_path='grade-quiz-answer')
    def grade_quiz_answer(self, request):
        """Grade individual quiz answer"""
        answer_id = request.data.get('answer_id')
        points_earned = request.data.get('points_earned')
        teacher_comment = request.data.get('teacher_comment', '')
        
        if not answer_id or points_earned is None:
            return Response({'error': 'answer_id and points_earned are required'}, status=400)
        
        try:
            quiz_answer = get_object_or_404(QuizAnswer, id=answer_id)
            
            quiz_answer.points_earned = float(points_earned)
            quiz_answer.teacher_comment = teacher_comment
            quiz_answer.is_correct = float(points_earned) > 0
            quiz_answer.graded_at = timezone.now()
            quiz_answer.save()
            
            # Recalculate attempt score
            attempt = quiz_answer.attempt
            total_earned = QuizAnswer.objects.filter(attempt=attempt).aggregate(
                total=models.Sum('points_earned')
            )['total'] or 0
            
            total_possible = attempt.assignment.questions.aggregate(
                total=models.Sum('points')
            )['total'] or 1
            
            attempt.score = (total_earned / total_possible) * attempt.assignment.max_score
            attempt.save()
            
            return Response({
                'message': 'Answer graded successfully',
                'points_earned': float(points_earned),
                'attempt_score': attempt.score
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)