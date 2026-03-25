#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School

User = get_user_model()

try:
    # Get the first school
    school = School.objects.first()
    if not school:
        print("No schools found. Creating a demo school...")
        school = School.objects.create(
            name="Demo School",
            location="Demo Location",
            phone_number="123-456-7890",
            email="demo@school.com"
        )
        print(f"Created school: {school.name}")
    
    # Create or update school admin user
    admin_email = "schooladmin@example.com"
    
    try:
        admin_user = User.objects.get(email=admin_email)
        print(f"School admin user already exists: {admin_user.email}")
    except User.DoesNotExist:
        admin_user = User.objects.create_user(
            email=admin_email,
            password="admin123",
            first_name="School",
            last_name="Admin",
            role="SCHOOL_ADMIN",
            school=school,
            is_active=True
        )
        print(f"Created school admin user: {admin_user.email}")
    
    # Update existing admin user to be school admin
    admin_user.role = "SCHOOL_ADMIN"
    admin_user.school = school
    admin_user.save()
    
    print(f"\nSchool Admin Details:")
    print(f"Email: {admin_user.email}")
    print(f"Password: admin123")
    print(f"Role: {admin_user.role}")
    print(f"School: {admin_user.school.name}")
    print(f"Active: {admin_user.is_active}")
    
except Exception as e:
    print(f"Error: {e}")