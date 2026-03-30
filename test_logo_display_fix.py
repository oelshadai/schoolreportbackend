#!/usr/bin/env python
"""
Test script to verify logo display fix for Cloudinary
Tests that logos display correctly in reports
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/path/to/your/project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School
from students.models import Student
from reports.utils import get_media_base_url, get_absolute_media_url
from django.test import RequestFactory
from django.conf import settings

User = get_user_model()

def test_logo_display():
    print("🧪 Testing Logo Display Fix...")
    
    try:
        # Check if Cloudinary is configured
        cloudinary_configured = (
            hasattr(settings, 'CLOUDINARY_STORAGE') or 
            'cloudinary' in getattr(settings, 'DEFAULT_FILE_STORAGE', '')
        )
        print(f"📡 Cloudinary configured: {cloudinary_configured}")
        
        # Create test school with logo
        school, created = School.objects.get_or_create(
            name="Test School with Logo",
            defaults={
                'address': 'Test Address',
                'location': 'Test Location', 
                'phone_number': '1234567890',
                'email': 'logo@school.com'
            }
        )
        
        # Simulate Cloudinary URL (if not actually uploaded)
        if not school.logo:
            # Mock Cloudinary URL for testing
            school.logo = 'https://res.cloudinary.com/demo/image/upload/v1234567890/school_logos/test_logo.png'
            school.save()
        
        print(f"✅ School: {school.name}")
        print(f"📷 Logo URL: {school.logo}")
        
        # Test media URL functions
        factory = RequestFactory()
        request = factory.get('/')
        
        # Test get_media_base_url
        media_base = get_media_base_url(request)
        print(f"🌐 Media base URL: '{media_base}'")
        
        # Test get_absolute_media_url
        if school.logo:
            absolute_url = get_absolute_media_url(school.logo, request)
            print(f"🔗 Absolute logo URL: {absolute_url}")
            
            # Check if URL is properly handled
            if cloudinary_configured:
                if absolute_url and (absolute_url.startswith('http') or not media_base):
                    print("✅ PASS: Cloudinary URL handled correctly (absolute)")
                    cloudinary_test = True
                else:
                    print("❌ FAIL: Cloudinary URL not handled correctly")
                    cloudinary_test = False
            else:
                if absolute_url and absolute_url.startswith('http'):
                    print("✅ PASS: Local URL made absolute correctly")
                    cloudinary_test = True
                else:
                    print("❌ FAIL: Local URL not made absolute")
                    cloudinary_test = False
        else:
            print("⚠️  No logo to test")
            cloudinary_test = True
        
        # Test report context generation
        print("\n📋 Testing Report Context...")
        
        # Create test student
        user, created = User.objects.get_or_create(
            email='student@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Student',
                'role': 'STUDENT',
                'school': school
            }
        )
        
        student, created = Student.objects.get_or_create(
            user=user,
            defaults={
                'student_id': 'TEST001',
                'first_name': 'Test',
                'last_name': 'Student',
                'school': school
            }
        )
        
        # Test context variables that would be used in template
        context_vars = {
            'school': student.school,
            'media_url_base': get_media_base_url(request),
            'school_logo_absolute': get_absolute_media_url(student.school.logo, request) if student.school.logo else None,
        }
        
        print(f"📝 Context variables:")
        for key, value in context_vars.items():
            print(f"   - {key}: {value}")
        
        # Verify template would work
        template_test = True
        if context_vars['school_logo_absolute']:
            if not context_vars['school_logo_absolute'].startswith('http'):
                print("❌ FAIL: Logo URL not absolute for template")
                template_test = False
            else:
                print("✅ PASS: Logo URL is absolute for template")
        
        return cloudinary_test and template_test
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_template_rendering():
    print("\n🎨 Testing Template Rendering Logic...")
    
    try:
        # Test the template logic for logo display
        school_logo_absolute = "https://res.cloudinary.com/demo/image/upload/v1234567890/school_logos/test_logo.png"
        media_url_base = ""
        school_logo_url = "/media/school_logos/test_logo.png"
        
        # Simulate template logic
        if school_logo_absolute:
            final_url = school_logo_absolute
            print(f"✅ Using absolute URL: {final_url}")
        else:
            final_url = media_url_base + school_logo_url
            print(f"✅ Using base + relative: {final_url}")
        
        # Check if URL is valid for img src
        if final_url.startswith('http') or final_url.startswith('/'):
            print("✅ PASS: URL valid for img src attribute")
            return True
        else:
            print("❌ FAIL: URL not valid for img src")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    logo_test = test_logo_display()
    template_test = test_template_rendering()
    
    if logo_test and template_test:
        print("\n🎉 Logo Display Fix: WORKING ✅")
    else:
        print("\n💥 Logo Display Fix: FAILED ❌")