#!/usr/bin/env python
import os
import sys
import django
import traceback
import logging

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import RequestFactory
from students.auth_views import student_login

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_student_login():
    """Test student login with detailed error tracking"""
    
    print("=== Student Login Debug Test ===")
    
    # Test data
    student_id = "2025BASIC_9001"
    password = "BS9001"
    
    try:
        # Check if student exists
        print(f"1. Checking if student {student_id} exists...")
        try:
            student = Student.objects.get(student_id=student_id)
            print(f"   [OK] Student found: {student.first_name} {student.last_name}")
            print(f"   - Student ID: {student.student_id}")
            print(f"   - Password set: {'Yes' if student.password else 'No'}")
            print(f"   - User linked: {'Yes' if student.user else 'No'}")
            
            if student.user:
                print(f"   - User email: {student.user.email}")
                print(f"   - User active: {student.user.is_active}")
        except Student.DoesNotExist:
            print(f"   [ERROR] Student {student_id} not found")
            return
        except Exception as e:
            print(f"   [ERROR] Error checking student: {e}")
            traceback.print_exc()
            return
        
        # Test password validation
        print(f"\n2. Testing password validation...")
        try:
            if student.password and student.password == password:
                print(f"   [OK] Direct password match")
            elif student.user and student.user.check_password(password):
                print(f"   [OK] User password match")
            else:
                print(f"   [ERROR] Password mismatch")
                print(f"   - Student password: {student.password}")
                print(f"   - Test password: {password}")
        except Exception as e:
            print(f"   [ERROR] Password validation error: {e}")
            traceback.print_exc()
        
        # Test token generation
        print(f"\n3. Testing token generation...")
        try:
            if student.user:
                refresh = RefreshToken.for_user(student.user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                print(f"   [OK] Tokens generated successfully")
                print(f"   - Access token length: {len(access_token)}")
                print(f"   - Refresh token length: {len(refresh_token)}")
            else:
                print(f"   [WARN] No user linked, would need to create user")
        except Exception as e:
            print(f"   [ERROR] Token generation error: {e}")
            traceback.print_exc()
        
        # Test the actual login view
        print(f"\n4. Testing actual login view...")
        try:
            factory = RequestFactory()
            request = factory.post('/api/auth/student-login/', {
                'username': student_id,
                'password': password
            }, content_type='application/json')
            
            # Add required attributes
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            request.META['HTTP_USER_AGENT'] = 'Test Client'
            
            response = student_login(request)
            print(f"   Response status: {response.status_code}")
            print(f"   Response data: {response.data}")
            
            if response.status_code == 200:
                print(f"   [OK] Login successful")
            else:
                print(f"   [ERROR] Login failed")
                
        except Exception as e:
            print(f"   [ERROR] Login view error: {e}")
            traceback.print_exc()
            
            # Check for specific error types
            if "Errno 22" in str(e):
                print(f"   [INFO] This is an OSError with invalid argument - likely file/path related")
            elif "OSError" in str(e):
                print(f"   [INFO] This is an OS-level error")
        
        print(f"\n=== Debug Test Complete ===")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_student_login()