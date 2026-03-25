#!/usr/bin/env python
"""
Quick test to verify the behavior endpoint is working
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from students.models import Student, Behaviour
from schools.models import School, Term, AcademicYear

User = get_user_model()

def test_behavior_endpoint():
    print("=== Testing Behavior Endpoint ===")
    
    # Create test data
    school, _ = School.objects.get_or_create(
        name="Test School",
        defaults={'address': 'Test', 'phone': '123', 'email': 'test@test.com'}
    )
    
    teacher, _ = User.objects.get_or_create(
        email='teacher@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Teacher',
            'role': 'TEACHER',
            'school': school
        }
    )
    teacher.set_password('password123')
    teacher.save()
    
    # Test the URL resolution
    try:
        url = reverse('behaviour-list')
        print(f"Behaviour list URL: {url}")
    except Exception as e:
        print(f"URL reverse error: {e}")
    
    # Test with client
    client = Client()
    
    # Test without authentication
    response = client.get('/api/students/behaviour/')
    print(f"GET /api/students/behaviour/ (no auth): {response.status_code}")
    print(f"Response content: {response.content.decode()[:200]}")
    
    # Test with authentication
    login_success = client.login(username=teacher.email, password='password123')
    print(f"Login successful: {login_success}")
    
    if login_success:
        response = client.get('/api/students/behaviour/')
        print(f"GET /api/students/behaviour/ (with auth): {response.status_code}")
        print(f"Response content: {response.content.decode()[:200]}")
    
    # Test the choices endpoint
    response = client.get('/api/students/behaviour/choices/')
    print(f"GET /api/students/behaviour/choices/: {response.status_code}")
    print(f"Response content: {response.content.decode()[:200]}")

if __name__ == '__main__':
    test_behavior_endpoint()