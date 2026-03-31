#!/usr/bin/env python
"""
Test Short Answer Grading Fix - Simple Version
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from assignments.models import Assignment, StudentAssignment

def test_grading_logic():
    """Test the grading type logic"""
    
    print("Testing Grading Type Logic")
    print("=" * 50)
    
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
        
        # Check student assignments
        student_assignments = StudentAssignment.objects.filter(assignment=assignment)
        submitted_count = student_assignments.filter(status='SUBMITTED').count()
        graded_count = student_assignments.filter(status='GRADED').count()
        
        print(f"  Student Assignments - Submitted: {submitted_count}, Graded: {graded_count}")
        
        # For short answer or hybrid quizzes, we expect SUBMITTED status
        if grading_type in ['SHORT_ANSWER_ONLY', 'HYBRID']:
            print(f"  Expected: Submissions should be SUBMITTED (waiting for teacher)")
        elif grading_type == 'MCQ_ONLY':
            print(f"  Expected: Submissions should be GRADED (auto-graded)")
        
        print("-" * 40)

if __name__ == '__main__':
    test_grading_logic()
    print("Test completed!")