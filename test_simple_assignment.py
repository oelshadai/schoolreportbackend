#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User
from schools.models import School, Teacher, Subject, Class, TeacherAssignment

def test_teacher_assignment_flow():
    """Test the complete teacher assignment flow"""
    print("=== TESTING TEACHER ASSIGNMENT FLOW ===")
    
    try:
        # Get or create a school
        school = School.objects.first()
        if not school:
            print("ERROR: No school found. Please create a school first.")
            return False
            
        print(f"Using school: {school.name}")
        
        # Get or create a user for teacher
        user, created = User.objects.get_or_create(
            username='test_teacher',
            defaults={
                'first_name': 'Test',
                'last_name': 'Teacher',
                'email': 'test.teacher@school.com'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print("Created test user")
        else:
            print("Using existing test user")
        
        # Get or create teacher
        teacher, created = Teacher.objects.get_or_create(
            user=user,
            school=school,
            defaults={
                'employee_id': 'T001',
                'phone': '1234567890',
                'address': '123 Test St',
                'qualification': 'Masters',
                'experience_years': 5,
                'salary': 50000.00
            }
        )
        if created:
            print("Created teacher")
        else:
            print("Using existing teacher")
        
        # Get or create subject
        subject, created = Subject.objects.get_or_create(
            name='Mathematics',
            school=school,
            defaults={
                'code': 'MATH101',
                'description': 'Basic Mathematics'
            }
        )
        if created:
            print("Created subject: Mathematics")
        else:
            print("Using existing subject: Mathematics")
        
        # Get or create class
        class_obj, created = Class.objects.get_or_create(
            name='Grade 10A',
            school=school,
            defaults={
                'grade_level': 10,
                'section': 'A',
                'capacity': 30
            }
        )
        if created:
            print("Created class: Grade 10A")
        else:
            print("Using existing class: Grade 10A")
        
        # Create teacher assignment
        assignment, created = TeacherAssignment.objects.get_or_create(
            teacher=teacher,
            subject=subject,
            class_assigned=class_obj,
            defaults={
                'academic_year': '2024-2025',
                'is_class_teacher': True
            }
        )
        
        if created:
            print("SUCCESS: Teacher assignment created")
        else:
            print("Teacher assignment already exists")
        
        # Verify the assignment
        print("\n=== ASSIGNMENT DETAILS ===")
        print(f"Teacher: {assignment.teacher.user.get_full_name()}")
        print(f"Subject: {assignment.subject.name}")
        print(f"Class: {assignment.class_assigned.name}")
        print(f"Academic Year: {assignment.academic_year}")
        print(f"Is Class Teacher: {assignment.is_class_teacher}")
        
        # Test queries
        print("\n=== TESTING QUERIES ===")
        
        # Get all assignments for this teacher
        teacher_assignments = TeacherAssignment.objects.filter(teacher=teacher)
        print(f"Total assignments for teacher: {teacher_assignments.count()}")
        
        # Get all teachers for this subject
        subject_teachers = TeacherAssignment.objects.filter(subject=subject)
        print(f"Teachers assigned to {subject.name}: {subject_teachers.count()}")
        
        # Get all assignments for this class
        class_assignments = TeacherAssignment.objects.filter(class_assigned=class_obj)
        print(f"Assignments for {class_obj.name}: {class_assignments.count()}")
        
        print("\n=== TEST COMPLETED SUCCESSFULLY ===")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_teacher_assignment_flow()
    if success:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)