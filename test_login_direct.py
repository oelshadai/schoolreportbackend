#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')

# Setup Django
django.setup()

# Now test the login
from django.test import RequestFactory
from students.auth_views import student_login
import json

def test_student_login():
    factory = RequestFactory()
    
    # Create a POST request with login data
    data = {
        'student_id': 'BS9001',
        'password': 'password123'
    }
    
    request = factory.post('/api/auth/student-login/', 
                          data=json.dumps(data),
                          content_type='application/json')
    
    # Add the data to request.data (simulate DRF)
    request.data = data
    
    try:
        response = student_login(request)
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_student_login()