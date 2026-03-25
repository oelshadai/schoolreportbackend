#!/usr/bin/env python3
"""
Test script to verify teacher profile functionality
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from accounts.models import User
from teachers.models import Teacher
from schools.models import School
from django.test import RequestFactory
from teachers.views import TeacherViewSet
from rest_framework.test import force_authenticate

def test_teacher_profile():
    """Test teacher profile endpoint"""
    print("Testing Teacher Profile Functionality...")
    
    # Create test data
    try:
        # Get or create a school
        school, created = School.objects.get_or_create(
            name="Test School",
            defaults={
                'location': 'Test Location',
                'contact_email': 'test@school.com',
                'phone_number': '1234567890'
            }
        )
        print(f"School: {school.name} ({'created' if created else 'found'})")
        
        # Get or create a teacher user
        user, created = User.objects.get_or_create(
            email='teacher@test.com',
            defaults={
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'TEACHER',
                'school': school,
                'is_active': True
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        print(f"User: {user.email} ({'created' if created else 'found'})")
        
        # Get or create teacher profile
        teacher, created = Teacher.objects.get_or_create(
            user=user,
            defaults={
                'employee_id': 'TCH001',
                'school': school,
                'qualification': 'Bachelor of Education',
                'experience_years': 5,
                'is_active': True
            }
        )
        print(f"Teacher: {teacher.get_full_name()} ({'created' if created else 'found'})")
        
        # Test the profile endpoint
        factory = RequestFactory()
        request = factory.get('/teachers/profile/')
        force_authenticate(request, user=user)
        
        # Create viewset instance and test profile action
        viewset = TeacherViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        response = viewset.profile(request)
        
        print(f"Profile endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Profile endpoint working correctly")
            data = response.data
            print(f"Profile data keys: {list(data.keys())}")
            print(f"Teacher name: {data.get('full_name')}")
            print(f"Employee ID: {data.get('employee_id')}")
            print(f"Email: {data.get('email')}")
        else:
            print(f"❌ Profile endpoint failed: {response.data}")
        
        # Test profile update
        update_data = {
            'first_name': 'Jane',
            'phone_number': '9876543210',
            'qualification': 'Master of Education'
        }
        
        request = factory.patch('/teachers/profile/', update_data, content_type='application/json')
        force_authenticate(request, user=user)
        request.data = update_data
        
        viewset.request = request
        response = viewset.profile(request)
        
        print(f"Profile update status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Profile update working correctly")
            updated_data = response.data
            print(f"Updated name: {updated_data.get('full_name')}")
            print(f"Updated phone: {updated_data.get('phone_number')}")
            print(f"Updated qualification: {updated_data.get('qualification')}")
        else:
            print(f"❌ Profile update failed: {response.data}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_teacher_profile()