#!/usr/bin/env python3
"""
Debug script to verify assignment access workflow
Run this to check data integrity and access patterns
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from assignments.models import Assignment, StudentAssignment
from students.models import Student
from schools.models import Class
from django.contrib.auth.models import User

def debug_assignment_access():
    print("=== ASSIGNMENT ACCESS DEBUG ===\n")
    
    # Get all published assignments
    assignments = Assignment.objects.filter(status='PUBLISHED').select_related('class_instance')
    print(f"Total Published Assignments: {assignments.count()}")
    
    for assignment in assignments[:5]:  # Check first 5
        print(f"\n--- Assignment: {assignment.title} (ID: {assignment.id}) ---")
        print(f"Class: {assignment.class_instance}")
        print(f"Class ID: {assignment.class_instance.id if assignment.class_instance else 'None'}")
        
        # Check students in this class
        if assignment.class_instance:
            students_in_class = assignment.class_instance.students.all()
            print(f"Students in class: {students_in_class.count()}")
            
            # Check StudentAssignment records
            student_assignments = StudentAssignment.objects.filter(assignment=assignment)
            print(f"StudentAssignment records: {student_assignments.count()}")
            
            # Check for mismatches
            for student in students_in_class[:3]:  # Check first 3 students
                has_assignment = StudentAssignment.objects.filter(
                    assignment=assignment,
                    student=student
                ).exists()
                print(f"  Student {student.student_id}: Has assignment record = {has_assignment}")
                
                # Check current_class
                print(f"    Student current_class: {student.current_class}")
                print(f"    Class match: {student.current_class == assignment.class_instance if student.current_class else False}")
    
    print("\n=== POTENTIAL ISSUES ===")
    
    # Check for students without current_class
    students_no_class = Student.objects.filter(current_class__isnull=True)
    print(f"Students without current_class: {students_no_class.count()}")
    
    # Check for assignments without class
    assignments_no_class = Assignment.objects.filter(class_instance__isnull=True, status='PUBLISHED')
    print(f"Published assignments without class: {assignments_no_class.count()}")
    
    # Check for orphaned StudentAssignments
    orphaned = StudentAssignment.objects.filter(
        assignment__status='PUBLISHED'
    ).exclude(
        student__current_class=models.F('assignment__class_instance')
    ).count()
    print(f"Potentially orphaned StudentAssignments: {orphaned}")

if __name__ == '__main__':
    debug_assignment_access()