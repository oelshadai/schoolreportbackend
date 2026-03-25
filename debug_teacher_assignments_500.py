#!/usr/bin/env python
"""
Debug script to test teacher assignments endpoint
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def test_teacher_assignments():
    """Test the teacher assignments endpoint that's causing 500 error"""
    print("Testing teacher assignments endpoint...")
    
    try:
        # Get a teacher user
        teacher = User.objects.filter(role='TEACHER').first()
        if not teacher:
            print("No teacher found in database")
            return
        
        print(f"Found teacher: {teacher.email}")
        
        # Create API client
        client = APIClient()
        
        # Generate JWT token
        refresh = RefreshToken.for_user(teacher)
        access_token = str(refresh.access_token)
        
        # Set authorization header
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Make request to assignments endpoint
        response = client.get('/api/teachers/assignments/')
        
        print(f"Response status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Response data: {response.data}")
        else:
            print(f"Response content: {response.content.decode()}")
        
        # Try to call the function directly to see the actual error
        print("\nTesting direct function call...")
        from teachers.simple_assignments import simple_teacher_assignments
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/teachers/assignments/')
        request.user = teacher
        
        try:
            direct_response = simple_teacher_assignments(request)
            print(f"Direct call status: {direct_response.status_code}")
            print(f"Direct call data: {direct_response.data}")
        except Exception as e:
            print(f"Direct call error: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_teacher_assignments()