#!/usr/bin/env python3
"""
Fix student assignment synchronization issue
Ensures assignments created by teachers are visible to students
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

def sync_assignments_to_students():
    """Sync all published assignments to students"""
    
    print("Syncing assignments to students...")
    
    # Get all published assignments
    published_assignments = Assignment.objects.filter(status='PUBLISHED')
    print(f"Found {published_assignments.count()} published assignments")
    
    created_count = 0
    updated_count = 0
    
    for assignment in published_assignments:
        print(f"\nProcessing: {assignment.title}")
        print(f"   Class: {assignment.class_instance}")
        print(f"   Created by: {assignment.created_by}")
        
        # Get all students in the assignment's class
        if assignment.class_instance:
            students = Student.objects.filter(current_class=assignment.class_instance)
            print(f"   Students in class: {students.count()}")
            
            for student in students:
                student_assignment, created = StudentAssignment.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={'status': 'NOT_STARTED'}
                )
                
                if created:
                    created_count += 1
                    print(f"   Created assignment for {student.get_full_name()}")
                else:
                    updated_count += 1
                    print(f"   Assignment already exists for {student.get_full_name()}")
    
    print(f"\nSync complete!")
    print(f"   Created: {created_count} new student assignments")
    print(f"   Existing: {updated_count} assignments")
    
    return created_count, updated_count

def verify_student_access():
    """Verify students can access their assignments"""
    
    print("\nVerifying student assignment access...")
    
    students = Student.objects.filter(user__isnull=False)
    
    for student in students:
        assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        )
        
        print(f"Student: {student.get_full_name()} ({student.student_id})")
        print(f"  Class: {student.current_class}")
        print(f"  Assignments: {assignments.count()}")
        
        if assignments.exists():
            for sa in assignments[:3]:  # Show first 3
                print(f"    - {sa.assignment.title} ({sa.status})")
        else:
            print(f"    WARNING: No assignments found!")

def create_test_student_if_needed():
    """Create a test student if none exists"""
    
    if not Student.objects.exists():
        print("\nCreating test student...")
        
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
        
        # Create student
        student = Student.objects.create(
            school=school,
            student_id="STD001",
            first_name="Test",
            last_name="Student",
            current_class=test_class,
            password="password123"
        )
        
        print(f"Created test student: {student.get_full_name()}")
        print(f"   Student ID: {student.student_id}")
        print(f"   Password: {student.password}")
        
        return student
    
    return None

if __name__ == "__main__":
    print("Starting assignment synchronization fix...")
    
    # Create test student if needed
    create_test_student_if_needed()
    
    # Sync assignments to students
    sync_assignments_to_students()
    
    # Verify access
    verify_student_access()
    
    print("\nAssignment sync fix completed!")