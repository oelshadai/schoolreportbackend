#!/usr/bin/env python
"""
Test script to verify teacher creation fix
Tests that school field is automatically set from admin's school
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/path/to/your/project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from teachers.serializers import TeacherCreateSerializer
from schools.models import School
from django.test import RequestFactory

User = get_user_model()

def test_teacher_creation():
    print("🧪 Testing Teacher Creation Fix...")
    
    try:
        # Get or create a test school
        school, created = School.objects.get_or_create(
            name="Test School",
            defaults={
                'address': 'Test Address',
                'location': 'Test Location',
                'phone_number': '1234567890',
                'email': 'test@school.com'
            }
        )
        print(f"✅ School: {school.name} (ID: {school.id})")
        
        # Get or create a test admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Admin',
                'role': 'SCHOOL_ADMIN',
                'school': school,
                'is_school_admin': True
            }
        )
        if created:
            admin_user.set_password('testpass123')
            admin_user.save()
        
        print(f"✅ Admin User: {admin_user.email} (School: {admin_user.school.name})")
        
        # Create mock request with admin user
        factory = RequestFactory()
        request = factory.post('/teachers/')
        request.user = admin_user
        
        # Test teacher creation data (WITHOUT school field)
        teacher_data = {
            'employee_id': 'TEST001',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@test.com',
            'password': 'testpass123',
            'qualification': 'Bachelor of Education',
            'experience_years': 5,
            'phone_number': '0987654321'
        }
        
        print(f"📝 Teacher Data (NO school field): {list(teacher_data.keys())}")
        
        # Test serializer
        serializer = TeacherCreateSerializer(data=teacher_data, context={'request': request})
        
        if serializer.is_valid():
            teacher = serializer.save()
            print(f"✅ SUCCESS: Teacher created!")
            print(f"   - Name: {teacher.get_full_name()}")
            print(f"   - Email: {teacher.user.email}")
            print(f"   - School: {teacher.school.name}")
            print(f"   - School ID: {teacher.school.id}")
            print(f"   - Admin's School ID: {admin_user.school.id}")
            
            # Verify school is correctly set
            if teacher.school.id == admin_user.school.id:
                print("✅ PASS: School automatically set from admin's school")
                return True
            else:
                print("❌ FAIL: School not set correctly")
                return False
        else:
            print(f"❌ FAIL: Serializer validation failed")
            print(f"   Errors: {serializer.errors}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_teacher_creation()
    if success:
        print("\n🎉 Teacher Creation Fix: WORKING ✅")
    else:
        print("\n💥 Teacher Creation Fix: FAILED ❌")