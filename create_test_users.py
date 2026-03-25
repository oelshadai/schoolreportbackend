#!/usr/bin/env python3
"""
Production-Ready Test Users Creation
Creates test users for immediate authentication testing
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from schools.models import School
from students.models import Student
from teachers.models import Teacher
from django.contrib.auth.hashers import make_password

def create_production_test_users():
    """Create production-ready test users"""
    print("🚀 Creating production-ready test users...")
    
    # Create test school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'address': 'Test Address',
            'phone_number': '1234567890',
            'email': 'test@school.com'
        }
    )
    print(f"✅ School: {school.name} ({'created' if created else 'exists'})")
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        email='admin@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Admin',
            'role': 'SCHOOL_ADMIN',
            'school': school,
            'is_active': True
        }
    )
    admin_user.set_password('testpass123')
    admin_user.save()
    print(f"✅ Admin: admin@test.com / testpass123 ({'created' if created else 'updated'})")
    
    # Create teacher user
    teacher_user, created = User.objects.get_or_create(
        email='teacher@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Teacher',
            'role': 'TEACHER',
            'school': school,
            'is_active': True
        }
    )
    teacher_user.set_password('testpass123')
    teacher_user.save()
    print(f"✅ Teacher: teacher@test.com / testpass123 ({'created' if created else 'updated'})")
    
    # Create teacher profile
    teacher_profile, created = Teacher.objects.get_or_create(
        user=teacher_user,
        defaults={
            'school': school,
            'employee_id': 'TEACH001',
            'qualification': 'Bachelor of Education',
            'is_active': True
        }
    )
    print(f"✅ Teacher profile: TEACH001 ({'created' if created else 'exists'})")
    
    # Create student user
    student_user, created = User.objects.get_or_create(
        email='student@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Student',
            'role': 'STUDENT',
            'school': school,
            'is_active': True
        }
    )
    student_user.set_password('testpass123')
    student_user.save()
    print(f"✅ Student user: student@test.com / testpass123 ({'created' if created else 'updated'})")
    
    # Create student profile
    student, created = Student.objects.get_or_create(
        student_id='TEST001',
        defaults={
            'user': student_user,
            'school': school,
            'first_name': 'Test',
            'last_name': 'Student',
            'date_of_birth': '2005-01-01',
            'is_active': True
        }
    )
    print(f"✅ Student: TEST001 / testpass123 ({'created' if created else 'exists'})")
    
    print("\n🎉 Production test users created successfully!")
    print("\n🔑 Credentials for testing:")
    print("   Admin: admin@test.com / testpass123")
    print("   Teacher: teacher@test.com / testpass123")
    print("   Student: TEST001 / testpass123")
    print("\n✅ Ready for production testing!")

if __name__ == "__main__":
    create_production_test_users()