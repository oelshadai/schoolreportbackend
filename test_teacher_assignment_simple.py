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
    """Test the complete teacher assignment workflow"""
    print("=== TESTING TEACHER ASSIGNMENT FLOW ===")
    
    try:
        # 1. Get or create a school
        school, created = School.objects.get_or_create(
            name="Test High School",
            defaults={
                'address': "123 Test Street",
                'phone': "555-0123",
                'email': "test@school.edu"
            }
        )
        print(f"[OK] Using school: {school.name}")
        
        # 2. Create a test user for teacher
        user, created = User.objects.get_or_create(
            username="test_teacher",
            defaults={
                'first_name': "John",
                'last_name': "Doe",
                'email': "john.doe@school.edu"
            }
        )
        print(f"[OK] Created/found user: {user.username}")
        
        # 3. Create a teacher
        teacher, created = Teacher.objects.get_or_create(
            user=user,
            school=school,
            defaults={
                'employee_id': "T001",
                'phone': "555-0124",
                'address': "456 Teacher Lane",
                'qualification': "M.Ed Mathematics",
                'experience_years': 5,
                'salary': 50000.00
            }
        )
        print(f"[OK] Created/found teacher: {teacher.user.get_full_name()}")
        
        # 4. Create subjects
        math_subject, created = Subject.objects.get_or_create(
            name="Mathematics",
            school=school,
            defaults={'code': 'MATH', 'description': 'Mathematics subject'}
        )
        
        physics_subject, created = Subject.objects.get_or_create(
            name="Physics", 
            school=school,
            defaults={'code': 'PHY', 'description': 'Physics subject'}
        )
        print(f"[OK] Created subjects: {math_subject.name}, {physics_subject.name}")
        
        # 5. Create classes
        class_10a, created = Class.objects.get_or_create(
            name="10A",
            school=school,
            defaults={'grade_level': 10, 'section': 'A'}
        )
        
        class_10b, created = Class.objects.get_or_create(
            name="10B",
            school=school, 
            defaults={'grade_level': 10, 'section': 'B'}
        )
        print(f"[OK] Created classes: {class_10a.name}, {class_10b.name}")
        
        # 6. Create teacher assignments
        assignment1, created = TeacherAssignment.objects.get_or_create(
            teacher=teacher,
            subject=math_subject,
            class_assigned=class_10a,
            defaults={
                'academic_year': '2024-25',
                'is_class_teacher': True
            }
        )
        
        assignment2, created = TeacherAssignment.objects.get_or_create(
            teacher=teacher,
            subject=physics_subject, 
            class_assigned=class_10b,
            defaults={
                'academic_year': '2024-25',
                'is_class_teacher': False
            }
        )
        print(f"[OK] Created assignments:")
        print(f"    - {teacher.user.get_full_name()} -> {math_subject.name} -> {class_10a.name}")
        print(f"    - {teacher.user.get_full_name()} -> {physics_subject.name} -> {class_10b.name}")
        
        # 7. Test queries
        print("\n=== TESTING QUERIES ===")
        
        # Get all assignments for the teacher
        teacher_assignments = TeacherAssignment.objects.filter(teacher=teacher)
        print(f"[OK] Teacher has {teacher_assignments.count()} assignments")
        
        # Get all teachers for a subject
        math_teachers = TeacherAssignment.objects.filter(subject=math_subject)
        print(f"[OK] Mathematics has {math_teachers.count()} teacher(s)")
        
        # Get all subjects for a class
        class_10a_subjects = TeacherAssignment.objects.filter(class_assigned=class_10a)
        print(f"[OK] Class 10A has {class_10a_subjects.count()} subject(s)")
        
        # Get class teacher
        class_teacher = TeacherAssignment.objects.filter(
            class_assigned=class_10a, 
            is_class_teacher=True
        ).first()
        if class_teacher:
            print(f"[OK] Class teacher for 10A: {class_teacher.teacher.user.get_full_name()}")
        
        # 8. Test assignment details
        print("\n=== ASSIGNMENT DETAILS ===")
        for assignment in teacher_assignments:
            print(f"Teacher: {assignment.teacher.user.get_full_name()}")
            print(f"Subject: {assignment.subject.name}")
            print(f"Class: {assignment.class_assigned.name}")
            print(f"Academic Year: {assignment.academic_year}")
            print(f"Class Teacher: {'Yes' if assignment.is_class_teacher else 'No'}")
            print(f"Created: {assignment.created_at}")
            print("---")
        
        print("\n[SUCCESS] All teacher assignment tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_teacher_assignment_flow()
    sys.exit(0 if success else 1)