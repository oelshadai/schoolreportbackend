#!/usr/bin/env python
"""
Fix Existing Incorrectly Graded Submissions
Reset submissions with short answer questions back to SUBMITTED status
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from assignments.models import Assignment, StudentAssignment, QuizAttempt
from django.utils import timezone

def fix_incorrectly_graded_submissions():
    """Fix submissions that were incorrectly marked as GRADED"""
    
    print("=" * 60)
    print("Fixing Incorrectly Graded Submissions")
    print("=" * 60)
    
    # Find assignments with short answer questions
    assignments_with_short_answers = Assignment.objects.filter(
        assignment_type__in=['QUIZ', 'EXAM'],
        has_short_answer_questions=True,
        status='PUBLISHED'
    )
    
    fixed_count = 0
    
    for assignment in assignments_with_short_answers:
        grading_type = assignment.get_quiz_grading_type()
        
        print(f"Assignment: {assignment.title}")
        print(f"  Grading Type: {grading_type}")
        
        if grading_type in ['SHORT_ANSWER_ONLY', 'HYBRID']:
            # Find student assignments that are incorrectly marked as GRADED
            incorrectly_graded = StudentAssignment.objects.filter(
                assignment=assignment,
                status='GRADED',
                graded_at__isnull=True  # No manual grading timestamp
            )
            
            print(f"  Found {incorrectly_graded.count()} incorrectly graded submissions")
            
            for sa in incorrectly_graded:
                print(f"    Fixing: {sa.student.get_full_name()}")
                
                # Reset to SUBMITTED status
                sa.status = 'SUBMITTED'
                sa.score = None  # Remove auto-calculated score
                sa.graded_at = None
                sa.save()
                
                # Also fix the QuizAttempt if it exists
                try:
                    quiz_attempt = QuizAttempt.objects.get(
                        assignment=assignment,
                        student=sa.student
                    )
                    if quiz_attempt.status == 'GRADED':
                        quiz_attempt.status = 'SUBMITTED'
                        quiz_attempt.save()
                        print(f"      Also fixed QuizAttempt")
                except QuizAttempt.DoesNotExist:
                    pass
                
                fixed_count += 1
        
        print("-" * 40)
    
    print(f"\nFixed {fixed_count} incorrectly graded submissions")
    print("These submissions now require teacher grading.")

def show_current_status():
    """Show current status of all quiz submissions"""
    
    print("\n" + "=" * 60)
    print("Current Status of Quiz Submissions")
    print("=" * 60)
    
    assignments = Assignment.objects.filter(
        assignment_type__in=['QUIZ', 'EXAM'],
        status='PUBLISHED'
    )
    
    for assignment in assignments:
        grading_type = assignment.get_quiz_grading_type()
        student_assignments = StudentAssignment.objects.filter(assignment=assignment)
        
        submitted_count = student_assignments.filter(status='SUBMITTED').count()
        graded_count = student_assignments.filter(status='GRADED').count()
        not_started_count = student_assignments.filter(status='NOT_STARTED').count()
        
        print(f"Assignment: {assignment.title}")
        print(f"  Grading Type: {grading_type}")
        print(f"  Not Started: {not_started_count}")
        print(f"  Submitted: {submitted_count}")
        print(f"  Graded: {graded_count}")
        
        if grading_type in ['SHORT_ANSWER_ONLY', 'HYBRID']:
            if submitted_count > 0:
                print(f"  Status: OK - {submitted_count} submissions waiting for teacher")
            if graded_count > 0:
                print(f"  Status: OK - {graded_count} submissions graded by teacher")
        elif grading_type == 'MCQ_ONLY':
            if graded_count > 0:
                print(f"  Status: OK - {graded_count} MCQ submissions auto-graded")
        
        print("-" * 40)

if __name__ == '__main__':
    show_current_status()
    
    print("\nDo you want to fix incorrectly graded submissions? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        fix_incorrectly_graded_submissions()
        print("\nShowing updated status:")
        show_current_status()
    else:
        print("No changes made.")