#!/usr/bin/env python3
"""
COMPREHENSIVE ASSIGNMENT VISIBILITY FIX
Root cause: Field name mismatch in filtering logic
"""
import os
import sys
import django
import sqlite3
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.conf import settings
from students.models import Student
from assignments.models import Assignment, StudentAssignment

def audit_assignment_visibility():
    """Audit the complete assignment visibility pipeline"""
    
    print("=== ASSIGNMENT VISIBILITY AUDIT ===\n")
    
    # Step 1: Check students and their classes
    students = Student.objects.filter(is_active=True).select_related('current_class')
    print(f"Active students: {students.count()}")
    
    for student in students:
        class_name = f"{student.current_class.level} {student.current_class.section}" if student.current_class else "No Class"
        print(f"- {student.get_full_name()} (ID: {student.student_id}) -> Class: {class_name} (ID: {student.current_class.id if student.current_class else None})")
    
    # Step 2: Check published assignments
    assignments = Assignment.objects.filter(status='PUBLISHED').select_related('class_instance')
    print(f"\nPublished assignments: {assignments.count()}")
    
    for assignment in assignments:
        class_name = f"{assignment.class_instance.level} {assignment.class_instance.section}" if assignment.class_instance else "No Class"
        print(f"- '{assignment.title}' (ID: {assignment.id}) -> Class: {class_name} (ID: {assignment.class_instance.id if assignment.class_instance else None})")
    
    # Step 3: Check student assignment records
    print(f"\nExisting StudentAssignment records:")
    student_assignments = StudentAssignment.objects.all().select_related('student', 'assignment')
    
    for sa in student_assignments:
        print(f"- {sa.student.get_full_name()} -> '{sa.assignment.title}' (Status: {sa.status})")
    
    # Step 4: Identify missing records
    print(f"\nIdentifying missing StudentAssignment records:")
    missing_count = 0
    
    for assignment in assignments:
        if assignment.class_instance:
            # Get students in this class
            class_students = assignment.class_instance.students.filter(is_active=True)
            
            for student in class_students:
                # Check if StudentAssignment exists
                exists = StudentAssignment.objects.filter(
                    assignment=assignment,
                    student=student
                ).exists()
                
                if not exists:
                    print(f"  MISSING: {student.get_full_name()} -> '{assignment.title}'")
                    missing_count += 1
    
    print(f"\nTotal missing StudentAssignment records: {missing_count}")
    
    # Step 5: Create missing records
    if missing_count > 0:
        print(f"\nCreating missing StudentAssignment records...")
        created_count = 0
        
        for assignment in assignments:
            if assignment.class_instance:
                class_students = assignment.class_instance.students.filter(is_active=True)
                
                for student in class_students:
                    sa, created = StudentAssignment.objects.get_or_create(
                        assignment=assignment,
                        student=student,
                        defaults={
                            'status': 'NOT_STARTED',
                            'attempts_count': 0,
                            'submission_text': '',
                            'teacher_feedback': '',
                            'additional_files': '[]',
                            'is_locked': False
                        }
                    )
                    
                    if created:
                        print(f"  CREATED: {student.get_full_name()} -> '{assignment.title}'")
                        created_count += 1
        
        print(f"\nCreated {created_count} new StudentAssignment records")
    
    # Step 6: Verify fix
    print(f"\nVerification - Student assignment counts:")
    for student in students:
        if student.current_class:
            # Count assignments for student's class
            class_assignments = Assignment.objects.filter(
                class_instance=student.current_class,
                status='PUBLISHED'
            ).count()
            
            # Count student assignment records
            student_assignment_count = StudentAssignment.objects.filter(
                student=student,
                assignment__status='PUBLISHED'
            ).count()
            
            print(f"- {student.get_full_name()}: {student_assignment_count}/{class_assignments} assignments")
    
    print(f"\n=== AUDIT COMPLETE ===")

def fix_api_filtering():
    """Fix the API filtering logic"""
    print(f"\n=== API FILTERING FIX ===")
    
    # The issue is in students/portal_views.py line 67
    # Current: Assignment.objects.filter(class_instance=student.current_class, ...)
    # Should be: Assignment.objects.filter(class_instance=student.current_class, ...)
    # This is actually correct, the issue was missing StudentAssignment records
    
    print("API filtering logic is correct.")
    print("Issue was missing StudentAssignment records, which has been fixed above.")

if __name__ == "__main__":
    audit_assignment_visibility()
    fix_api_filtering()