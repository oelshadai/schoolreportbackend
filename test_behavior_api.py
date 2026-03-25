#!/usr/bin/env python
"""
Test script to check behavior API endpoint and create test data
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student, Behaviour
from schools.models import School, Term, AcademicYear
from django.test import Client
from django.urls import reverse
import json

User = get_user_model()

def test_behavior_api():
    print("=== Testing Behavior API ===")
    
    # Get or create a test school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'address': 'Test Address',
            'phone': '1234567890',
            'email': 'test@school.com'
        }
    )
    print(f"School: {school.name} ({'created' if created else 'exists'})")
    
    # Get or create a test teacher user
    teacher_user, created = User.objects.get_or_create(
        email='teacher@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Teacher',
            'role': 'TEACHER',
            'school': school
        }
    )
    if created:
        teacher_user.set_password('password123')
        teacher_user.save()
    print(f"Teacher: {teacher_user.email} ({'created' if created else 'exists'})")
    
    # Get or create academic year and term
    academic_year, created = AcademicYear.objects.get_or_create(
        school=school,
        name="2024/2025",
        defaults={
            'start_date': '2024-09-01',
            'end_date': '2025-07-31',
            'is_current': True
        }
    )
    print(f"Academic Year: {academic_year.name} ({'created' if created else 'exists'})")
    
    term, created = Term.objects.get_or_create(
        academic_year=academic_year,
        name="First Term",
        defaults={
            'start_date': '2024-09-01',
            'end_date': '2024-12-15'
        }
    )
    print(f"Term: {term.name} ({'created' if created else 'exists'})")
    
    # Get or create a test student
    student, created = Student.objects.get_or_create(
        school=school,
        student_id='TEST001',
        defaults={
            'first_name': 'Test',
            'last_name': 'Student',
            'gender': 'M',
            'date_of_birth': '2010-01-01',
            'guardian_name': 'Test Guardian',
            'guardian_phone': '1234567890',
            'guardian_address': 'Test Address',
            'admission_date': '2024-09-01'
        }
    )
    print(f"Student: {student.get_full_name()} ({'created' if created else 'exists'})")
    
    # Create a test behavior record
    behavior, created = Behaviour.objects.get_or_create(
        student=student,
        term=term,
        defaults={
            'conduct': 'GOOD',
            'attitude': 'VERY_GOOD',
            'interest': 'READING_WRITING',
            'punctuality': 'EXCELLENT',
            'class_teacher_remarks': 'Test student shows good behavior and attitude.',
            'promoted_to': 'Basic 8'
        }
    )
    print(f"Behavior Record: {behavior} ({'created' if created else 'exists'})")
    
    # Test the API endpoint
    client = Client()
    
    # Login as teacher
    login_success = client.login(username=teacher_user.email, password='password123')
    print(f"Login successful: {login_success}")
    
    if not login_success:
        # Try to set password and login again
        teacher_user.set_password('password123')
        teacher_user.save()
        login_success = client.login(username=teacher_user.email, password='password123')
        print(f"Login after password reset: {login_success}")
    
    # Test GET request to behavior endpoint
    try:
        response = client.get('/api/students/behaviour/')
        print(f"GET /api/students/behaviour/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error response: {response.content.decode()}")
            
    except Exception as e:
        print(f"Error testing API: {e}")
    
    # Test choices endpoint
    try:
        response = client.get('/api/students/behaviour/choices/')
        print(f"GET /api/students/behaviour/choices/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Choices data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error response: {response.content.decode()}")
            
    except Exception as e:
        print(f"Error testing choices API: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == '__main__':
    test_behavior_api()