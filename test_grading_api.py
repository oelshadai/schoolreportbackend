#!/usr/bin/env python
"""
Test Grading API Endpoints
Verify that the grading system is working correctly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from assignments.models import Assignment, StudentAssignment, QuizAttempt, QuizAnswer, Question
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()

def test_grading_endpoints():
    """Test the grading system"""
    
    print("=" * 60)
    print("Testing Grading System")
    print("=" * 60)
    
    # Find the quiz with pending submissions
    assignment = Assignment.objects.filter(
        title='test 1',
        assignment_type='QUIZ',
        has_short_answer_questions=True
    ).first()
    
    if not assignment:
        print("ERROR: Quiz 'test 1' not found")
        return
    
    print(f"\nAssignment: {assignment.title}")
    print(f"Type: {assignment.assignment_type}")
    print(f"Grading Type: {assignment.get_quiz_grading_type()}")
    print(f"Max Score: {assignment.max_score}")
    
    # Find pending submissions
    pending_submissions = StudentAssignment.objects.filter(
        assignment=assignment,
        status='SUBMITTED'
    )
    
    print(f"\nPending Submissions: {pending_submissions.count()}")
    
    for sa in pending_submissions:
        print(f"\n  Student: {sa.student.get_full_name()}")
        print(f"  Status: {sa.status}")
        print(f"  Submitted: {sa.submitted_at}")
        
        # Find the quiz attempt
        try:
            quiz_attempt = QuizAttempt.objects.get(
                assignment=assignment,
                student=sa.student
            )
            
            print(f"  Quiz Attempt ID: {quiz_attempt.id}")
            print(f"  Attempt Status: {quiz_attempt.status}")
            
            # Get all answers
            answers = QuizAnswer.objects.filter(attempt=quiz_attempt)
            print(f"  Total Answers: {answers.count()}")
            
            # Show each answer
            for answer in answers:
                print(f"\n    Question {answer.question.order}: {answer.question.question_text[:50]}...")
                print(f"      Type: {answer.question.question_type}")
                print(f"      Points: {answer.question.points}")
                
                if answer.question.question_type == 'mcq':
                    print(f"      Selected: {answer.selected_option.option_text if answer.selected_option else 'None'}")
                    print(f"      Correct: {answer.is_correct}")
                    print(f"      Points Earned: {answer.points_earned}")
                elif answer.question.question_type == 'short_answer':
                    print(f"      Answer: {answer.answer_text[:100]}...")
                    print(f"      Graded: {answer.is_correct is not None}")
                    print(f"      Points Earned: {answer.points_earned}")
                    print(f"      Needs Manual Grading: {answer.is_correct is None}")
            
            # Test data for grading
            print(f"\n  API Test Data:")
            print(f"    Submission ID: quiz_{quiz_attempt.id}")
            print(f"    Student ID: {sa.student.id}")
            print(f"    Student Name: {sa.student.get_full_name()}")
            
        except QuizAttempt.DoesNotExist:
            print("  ERROR: Quiz attempt not found")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    # Show what the API should return
    print("\nExpected API Response for /assignments/grading/pending-grading/:")
    print(f"  - Assignment ID: {assignment.id}")
    print(f"  - Title: {assignment.title}")
    print(f"  - Pending Submissions: {pending_submissions.count()}")
    
    if pending_submissions.exists():
        sa = pending_submissions.first()
        try:
            quiz_attempt = QuizAttempt.objects.get(
                assignment=assignment,
                student=sa.student
            )
            print(f"\nExpected API Response for /assignments/grading/quiz_{quiz_attempt.id}/quiz-details/:")
            print(f"  - Attempt ID: {quiz_attempt.id}")
            print(f"  - Student: {sa.student.get_full_name()}")
            print(f"  - Questions: {QuizAnswer.objects.filter(attempt=quiz_attempt).count()}")
            
            # Show which questions need grading
            ungraded = QuizAnswer.objects.filter(
                attempt=quiz_attempt,
                question__question_type='short_answer',
                is_correct__isnull=True
            )
            print(f"  - Questions Needing Grading: {ungraded.count()}")
            
        except QuizAttempt.DoesNotExist:
            pass

if __name__ == '__main__':
    test_grading_endpoints()
