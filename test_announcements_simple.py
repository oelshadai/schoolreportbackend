#!/usr/bin/env python
import os
import django
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from schools.models import School

@override_settings(ALLOWED_HOSTS=['testserver'])
def test_announcements_endpoint():
    print("Testing Announcements Endpoint...")
    
    client = APIClient()
    User = get_user_model()
    
    try:
        # Get or create a school
        school, created = School.objects.get_or_create(
            name="Test School",
            defaults={
                'address': 'Test Address',
                'phone': '1234567890',
                'email': 'test@school.com'
            }
        )
        print(f"School: {school.name}")
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'ADMIN',
                'school': school,
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        print(f"Admin user: {admin_user.email}")
        
        # Force authenticate
        client.force_authenticate(user=admin_user)
        
        # Test GET announcements
        response = client.get('/api/announcements/')
        print(f"GET /api/announcements/ - Status: {response.status_code}")
        
        # Test POST announcement
        announcement_data = {
            'title': 'Test Announcement',
            'content': 'This is a test announcement for all students.',
            'audience': 'ALL',
            'is_pinned': False
        }
        
        response = client.post('/api/announcements/', announcement_data, format='json')
        print(f"POST /api/announcements/ - Status: {response.status_code}")
        
        if response.status_code == 201:
            print("SUCCESS: Announcement created successfully")
            announcement = response.json()
            print(f"Created announcement: {announcement.get('title')}")
        else:
            print(f"ERROR: Failed to create announcement")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_announcements_endpoint()