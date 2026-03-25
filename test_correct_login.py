#!/usr/bin/env python
import os
import django
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from django.contrib.auth import get_user_model
import requests
import json

def test_login():
    print("=== Testing Student Login ===\n")
    
    # Get student data
    try:
        student = Student.objects.get(student_id='2025BASIC_9001')
        print(f"Student: {student.first_name} {student.last_name}")
        print(f"Student ID: {student.student_id}")
        print(f"Password: {student.password}")
        
        if student.user:
            print(f"User email: {student.user.email}")
            print(f"User active: {student.user.is_active}")
        
        # Test login with correct credentials
        login_data = {
            'student_id': '2025BASIC_9001',
            'password': 'student123'
        }
        
        print(f"\nTesting login with:")
        print(f"Username: {login_data['student_id']}")
        print(f"Password: {login_data['password']}")
        
        # Make login request
        try:
            response = requests.post(
                'http://localhost:8000/api/students/login/',
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("\n[SUCCESS] Login worked!")
            else:
                print(f"\n[FAILED] Login failed: {response.json()}")
                
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Cannot connect to server. Is Django running?")
            print("Run: python manage.py runserver")
            
    except Student.DoesNotExist:
        print("Student not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_login()