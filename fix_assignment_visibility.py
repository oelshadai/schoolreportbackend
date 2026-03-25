#!/usr/bin/env python3
"""
PRODUCTION FIX: Assignment Visibility Pipeline
Fixes the critical data visibility issue where teacher assignments don't appear in student portal
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from assignments.models import Assignment, StudentAssignment
from schools.models import School, Class
from datetime import datetime

User = get_user_model()

def audit_assignment_visibility():
    """Comprehensive audit of assignment visibility pipeline"""
    
    print("=== ASSIGNMENT VISIBILITY AUDIT ===")
    
    # Step 1: Check published assignments
    published_assignments = Assignment.objects.filter(status='PUBLISHED')
    print(f"Total published assignments: {published_assignments.count()}")
    
    # Step 2: Check students with classes
    students_with_classes = Student.objects.filter(current_class__isnull=False)
    print(f"Students with classes: {students_with_classes.count()}")
    
    # Step 3: Check existing StudentAssignment records
    student_assignments = StudentAssignment.objects.all()
    print(f"Existing StudentAssignment records: {student_assignments.count()}")
    
    # Step 4: Identify missing StudentAssignment records
    missing_count = 0
    for assignment in published_assignments:
        if assignment.class_instance:
            students_in_class = assignment.class_instance.students.all()
            for student in students_in_class:
                if not StudentAssignment.objects.filter(
                    assignment=assignment,
                    student=student
                ).exists():
                    missing_count += 1
    
    print(f"Missing StudentAssignment records: {missing_count}")
    
    # Step 5: Show detailed breakdown by assignment
    print("\n=== ASSIGNMENT BREAKDOWN ===")
    for assignment in published_assignments:
        if assignment.class_instance:
            total_students = assignment.class_instance.students.count()
            assigned_students = StudentAssignment.objects.filter(assignment=assignment).count()
            print(f"Assignment: {assignment.title}")
            print(f"  Class: {assignment.class_instance}")
            print(f"  Students in class: {total_students}")
            print(f"  StudentAssignment records: {assigned_students}")
            print(f"  Missing: {total_students - assigned_students}")
            print()

def fix_assignment_visibility():
    """Fix assignment visibility by creating missing StudentAssignment records"""
    
    print("=== FIXING ASSIGNMENT VISIBILITY ===")
    
    published_assignments = Assignment.objects.filter(status='PUBLISHED')
    created_count = 0
    updated_count = 0
    error_count = 0
    
    for assignment in published_assignments:
        print(f"\nProcessing: {assignment.title}")
        print(f"  Class: {assignment.class_instance}")
        print(f"  Created by: {assignment.created_by}")
        
        if not assignment.class_instance:
            print(f"  ERROR: No class assigned to assignment {assignment.id}")
            error_count += 1
            continue
        
        # Get all students in the assignment's class
        students = assignment.class_instance.students.all()
        print(f"  Students in class: {students.count()}")
        
        for student in students:
            try:
                student_assignment, created = StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
                
                if created:
                    created_count += 1
                    print(f"    CREATED: Assignment for {student.get_full_name()}")
                else:
                    updated_count += 1
                    print(f"    EXISTS: Assignment for {student.get_full_name()}")
                    
            except Exception as e:
                error_count += 1
                print(f"    ERROR: Failed to create assignment for {student.get_full_name()}: {e}")
    
    print(f"\n=== SYNC RESULTS ===")
    print(f"Created: {created_count} new StudentAssignment records")
    print(f"Existing: {updated_count} records")
    print(f"Errors: {error_count} failures")
    
    return created_count, updated_count, error_count

def verify_student_portal_access():
    """Verify students can now access their assignments"""
    
    print("\n=== VERIFYING STUDENT PORTAL ACCESS ===")
    
    students = Student.objects.filter(current_class__isnull=False)
    
    for student in students[:5]:  # Check first 5 students
        print(f"\nStudent: {student.get_full_name()} ({student.student_id})")
        print(f"  Class: {student.current_class}")
        
        # Get assignments the way the API does it
        published_assignments = Assignment.objects.filter(
            class_instance=student.current_class,
            status='PUBLISHED'
        )
        
        student_assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        )
        
        print(f"  Published assignments in class: {published_assignments.count()}")
        print(f"  StudentAssignment records: {student_assignments.count()}")
        
        if student_assignments.exists():
            print("  ASSIGNMENTS:")
            for sa in student_assignments[:3]:  # Show first 3
                print(f"    - {sa.assignment.title} ({sa.status})")
        else:
            print("  WARNING: No assignments found!")

def create_test_data_if_needed():
    """Create test data if database is empty"""
    
    if not Student.objects.exists():
        print("\n=== CREATING TEST DATA ===")
        
        # Get or create school
        school, _ = School.objects.get_or_create(
            name="Test School",
            defaults={
                'address': 'Test Address',
                'phone': '1234567890',
                'email': 'test@school.com'
            }
        )
        
        # Get or create class
        test_class, _ = Class.objects.get_or_create(
            school=school,
            level="Grade 10A",
            defaults={'capacity': 30}
        )
        
        # Create test students
        for i in range(3):
            student = Student.objects.create(
                school=school,
                student_id=f"STD00{i+1}",
                first_name=f"Test{i+1}",
                last_name="Student",
                current_class=test_class,
                gender='M',
                date_of_birth='2005-01-01',
                guardian_name='Test Guardian',
                guardian_phone='1234567890',
                guardian_address='Test Address',
                admission_date='2023-01-01'
            )
            print(f"Created test student: {student.get_full_name()}")
        
        print(f"Created {Student.objects.count()} test students")

def run_comprehensive_fix():
    """Run the complete assignment visibility fix"""
    
    print("STARTING COMPREHENSIVE ASSIGNMENT VISIBILITY FIX")
    print("=" * 60)
    
    # Step 1: Create test data if needed
    create_test_data_if_needed()
    
    # Step 2: Audit current state
    audit_assignment_visibility()
    
    # Step 3: Fix visibility issues
    created, existing, errors = fix_assignment_visibility()
    
    # Step 4: Verify fix worked
    verify_student_portal_access()
    
    print("\n" + "=" * 60)
    print("ASSIGNMENT VISIBILITY FIX COMPLETED")
    print(f"Summary: {created} created, {existing} existing, {errors} errors")
    print("=" * 60)

if __name__ == "__main__":
    run_comprehensive_fix()