#!/usr/bin/env python
"""
Test Short Answer Grading Fix
Verify that assignments with short answer questions stay in SUBMITTED status
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from assignments.models import Assignment, StudentAssignment, Question, QuestionOption
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()

def test_short_answer_grading():
    """Test that short answer quizzes stay in SUBMITTED status"""
    
    print("=" * 60)
    print("Testing Short Answer Grading Fix")
    print("=" * 60)
    
    # Find a quiz assignment with short answer questions
    short_answer_assignments = Assignment.objects.filter(
        assignment_type='QUIZ',
        has_short_answer_questions=True,
        status='PUBLISHED'
    )
    
    if not short_answer_assignments.exists():
        print("No quiz assignments with short answer questions found.")
        return
    
    assignment = short_answer_assignments.first()
    print(f"Testing assignment: {assignment.title}")
    print(f"Assignment type: {assignment.assignment_type}")
    print(f"Has MCQ: {assignment.has_mcq_questions}")
    print(f"Has Short Answer: {assignment.has_short_answer_questions}")
    print(f"Grading type: {assignment.get_quiz_grading_type()}")
    
    # Find student assignments for this quiz
    student_assignments = StudentAssignment.objects.filter(
        assignment=assignment
    ).select_related('student')
    
    print(f"\nFound {student_assignments.count()} student assignments:")
    
    for sa in student_assignments:
        print(f"  Student: {sa.student.get_full_name()}")
        print(f"  Status: {sa.status}")
        print(f"  Score: {sa.score}")
        print(f"  Submitted: {sa.submitted_at}")
        print(f"  Graded: {sa.graded_at}")
        
        # Check if this should be SUBMITTED (not GRADED) for short answer quizzes
        grading_type = assignment.get_quiz_grading_type()
        if grading_type in ['SHORT_ANSWER_ONLY', 'HYBRID']:
            if sa.status == 'GRADED' and not sa.graded_at:
                print(f"  ⚠ WARNING: Status is GRADED but no graded_at timestamp!")
            elif sa.status == 'SUBMITTED':
                print(f"  ✓ CORRECT: Status is SUBMITTED (waiting for teacher)")
            elif sa.status == 'GRADED':
                print(f"  ✓ GRADED: Teacher has graded this submission")
        elif grading_type == 'MCQ_ONLY':
            if sa.status == 'GRADED':
                print(f"  ✓ CORRECT: MCQ-only quiz auto-graded")
        
        print("-" * 40)

def test_grading_logic():
    """Test the grading type logic"""
    
    print("\n" + "=" * 60)
    print("Testing Grading Type Logic")
    print("=" * 60)
    
    assignments = Assignment.objects.filter(
        assignment_type__in=['QUIZ', 'EXAM'],
        status='PUBLISHED'
    )
    
    for assignment in assignments:
        grading_type = assignment.get_quiz_grading_type()
        should_show_immediately = assignment.should_show_results_immediately()
        
        print(f"Assignment: {assignment.title}")
        print(f"  Type: {assignment.assignment_type}")
        print(f"  Has MCQ: {assignment.has_mcq_questions}")
        print(f"  Has Short Answer: {assignment.has_short_answer_questions}")
        print(f"  Grading Type: {grading_type}")
        print(f"  Show Results Immediately: {should_show_immediately}")
        
        # Verify logic
        if assignment.has_mcq_questions and assignment.has_short_answer_questions:
            assert grading_type == 'HYBRID', f"Expected HYBRID, got {grading_type}"
            assert not should_show_immediately, "HYBRID should not show results immediately"
        elif assignment.has_mcq_questions:
            assert grading_type == 'MCQ_ONLY', f"Expected MCQ_ONLY, got {grading_type}"
            assert should_show_immediately, "MCQ_ONLY should show results immediately"
        elif assignment.has_short_answer_questions:
            assert grading_type == 'SHORT_ANSWER_ONLY', f"Expected SHORT_ANSWER_ONLY, got {grading_type}"
            assert not should_show_immediately, "SHORT_ANSWER_ONLY should not show results immediately"
        
        print("  ✓ Logic verified")
        print("-" * 40)

if __name__ == '__main__':
    test_grading_logic()
    test_short_answer_grading()
    print("\n✓ Test completed!")