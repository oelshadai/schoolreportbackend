#!/usr/bin/env python
"""
Test assignments API endpoint
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import Class
from assignments.models import Assignment
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def test_assignments_api():
    """Test the assignments API endpoint"""
    
    # Get a teacher user
    teacher = User.objects.filter(role='TEACHER').first()
    if not teacher:
        print("No teacher found in database")
        return
    
    print(f"Testing with teacher: {teacher.email}")
    
    # Get a class taught by this teacher
    class_instance = Class.objects.filter(class_teacher=teacher).first()
    if not class_instance:
        print("No class found for this teacher")
        return
    
    print(f"Testing with class: {class_instance}")
    
    # Get assignments for this class
    assignments = Assignment.objects.filter(
        class_instance=class_instance,
        created_by=teacher
    )
    print(f"Found {assignments.count()} assignments for this teacher/class")
    
    for assignment in assignments:
        print(f"  - {assignment.title} (Status: {assignment.status})")
    
    # Test API endpoint
    client = APIClient()
    
    # Get JWT token for teacher
    refresh = RefreshToken.for_user(teacher)
    access_token = str(refresh.access_token)
    
    # Set authorization header
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    # Test the dashboard endpoint
    url = f'/api/assignments/teacher/dashboard/?class_id={class_instance.id}'
    print(f"\nTesting API endpoint: {url}")
    
    response = client.get(url)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("API Response:")
        print(f"  Class: {data.get('class', {}).get('name')}")
        print(f"  Student count: {data.get('class', {}).get('student_count')}")
        print(f"  Assignments count: {len(data.get('assignments', []))}")
        
        for assignment in data.get('assignments', []):
            print(f"    - {assignment.get('title')} ({assignment.get('status')})")
    else:
        print(f"API Error: {response.content.decode()}")

if __name__ == "__main__":
    test_assignments_api()