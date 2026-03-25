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
    # Check the admin user
    admin_user = User.objects.get(email='admin@example.com')
    print(f"Admin user found: {admin_user.email}")
    print(f"Role: {admin_user.role}")
    print(f"School: {admin_user.school}")
    print(f"Is active: {admin_user.is_active}")
    
    # Check if there are any schools
    schools = School.objects.all()
    print(f"\nTotal schools: {schools.count()}")
    
    if schools.exists():
        for school in schools:
            print(f"School: {school.name} (ID: {school.id})")
    
    # If admin has no school, assign the first one
    if not admin_user.school and schools.exists():
        first_school = schools.first()
        admin_user.school = first_school
        admin_user.save()
        print(f"\nAssigned school '{first_school.name}' to admin user")
    
except User.DoesNotExist:
    print("Admin user not found")
except Exception as e:
    print(f"Error: {e}")