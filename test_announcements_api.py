#!/usr/bin/env python
import os
import django
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from schools.models import School
import json

def test_announcements_api():
    print("Testing Announcements API...")
    
    # Create test client
    client = Client()
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
        print(f"School: {school.name} ({'created' if created else 'exists'})")
        
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
        print(f"Admin user: {admin_user.email} ({'created' if created else 'exists'})")
        
        # Login as admin
        login_response = client.post('/api/auth/admin/login/', {
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            access_token = login_data.get('access')
            print("✓ Admin login successful")
            
            # Test GET announcements
            headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
            get_response = client.get('/api/announcements/', **headers)
            print(f"GET /api/announcements/ - Status: {get_response.status_code}")
            
            # Test POST announcement
            announcement_data = {
                'title': 'Test Announcement',
                'content': 'This is a test announcement for all students.',
                'audience': 'ALL',
                'is_pinned': False
            }
            
            post_response = client.post(
                '/api/announcements/',
                data=json.dumps(announcement_data),
                content_type='application/json',
                **headers
            )
            print(f"POST /api/announcements/ - Status: {post_response.status_code}")
            
            if post_response.status_code == 201:
                print("✓ Announcement created successfully")
                announcement = post_response.json()
                print(f"  Created announcement: {announcement.get('title')}")
            else:
                print(f"✗ Failed to create announcement: {post_response.content.decode()}")
                
        else:
            print(f"✗ Admin login failed: {login_response.content.decode()}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_announcements_api()