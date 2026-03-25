#!/usr/bin/env python
"""
Create test teacher and class for API testing
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School, Class
from assignments.models import Assignment
from datetime import datetime

User = get_user_model()

def create_test_data():
    """Create test teacher, school, class and assignments"""
    
    # Create or get school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'address': "123 Test Street",
            'phone': "123-456-7890",
            'email': "test@school.com"
        }
    )
    print(f"School: {school.name} ({'created' if created else 'exists'})")
    
    # Create or get teacher
    teacher, created = User.objects.get_or_create(
        email="teacher@test.com",
        defaults={
            'first_name': "Test",
            'last_name': "Teacher",
            'role': "TEACHER",
            'school': school
        }
    )
    if created:
        teacher.set_password("password123")
        teacher.save()
    print(f"Teacher: {teacher.email} ({'created' if created else 'exists'})")
    
    # Create or get class
    class_instance, created = Class.objects.get_or_create(
        level="BASIC_5",
        section="A",
        school=school,
        defaults={
            'class_teacher': teacher,
            'capacity': 30
        }
    )
    
    # Ensure teacher is assigned as class teacher
    if not class_instance.class_teacher:
        class_instance.class_teacher = teacher
        class_instance.save()
        print(f"Assigned {teacher.email} as class teacher")
    
    print(f"Class: {class_instance} ({'created' if created else 'exists'})")
    
    # Create some class subjects for the teacher
    from schools.models import Subject, ClassSubject
    
    # Create or get subjects
    math_subject, _ = Subject.objects.get_or_create(
        name="Mathematics",
        defaults={'code': 'MATH', 'category': 'PRIMARY'}
    )
    
    english_subject, _ = Subject.objects.get_or_create(
        name="English Language",
        defaults={'code': 'ENG', 'category': 'PRIMARY'}
    )
    
    # Assign subjects to class with teacher
    math_assignment, created = ClassSubject.objects.get_or_create(
        class_instance=class_instance,
        subject=math_subject,
        defaults={'teacher': teacher}
    )
    if not math_assignment.teacher:
        math_assignment.teacher = teacher
        math_assignment.save()
    
    english_assignment, created = ClassSubject.objects.get_or_create(
        class_instance=class_instance,
        subject=english_subject,
        defaults={'teacher': teacher}
    )
    if not english_assignment.teacher:
        english_assignment.teacher = teacher
        english_assignment.save()
    
    print(f"Assigned subjects: Mathematics, English Language")
    
    print(f"Assigned subjects: Mathematics, English Language")
    
    # Create test assignments if none exist for this teacher
    existing_assignments = Assignment.objects.filter(
        class_instance=class_instance,
        created_by=teacher
    )
    
    if not existing_assignments.exists():
        assignments_data = [
            {"title": "Math Assignment 1", "status": "PUBLISHED"},
            {"title": "Science Project", "status": "DRAFT"},
            {"title": "English Essay", "status": "PUBLISHED"},
            {"title": "History Quiz", "status": "PUBLISHED"},
        ]
        
        for data in assignments_data:
            assignment = Assignment.objects.create(
                title=data["title"],
                description=f"Test description for {data['title']}",
                instructions=f"Complete the {data['title']} as instructed in class.",
                class_instance=class_instance,
                created_by=teacher,
                status=data["status"],
                due_date=datetime.now().date(),
                max_score=10,
                assignment_type='HOMEWORK'
            )
            print(f"Created assignment: {assignment.title} ({assignment.status})")
    else:
        print(f"Found {existing_assignments.count()} existing assignments for this teacher")
    
    print("\nTest data ready!")
    print(f"Teacher: {teacher.email}")
    print(f"Class: {class_instance}")
    print(f"Assignments created by teacher: {Assignment.objects.filter(created_by=teacher).count()}")
    return teacher, class_instance

if __name__ == "__main__":
    create_test_data()