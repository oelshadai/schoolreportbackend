#!/usr/bin/env python3
"""
Fix Windows-specific issues in student login
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from django.contrib.auth import get_user_model
import hashlib

def fix_student_login():
    """Fix student login issues"""
    print("=== FIXING STUDENT LOGIN ISSUES ===")
    
    # Check if the test student exists
    try:
        student = Student.objects.get(student_id='2025BASIC_9001')
        print(f"Found student: {student.first_name} {student.last_name}")
        print(f"Student ID: {student.student_id}")
        print(f"Password: {student.password}")
        
        # Ensure password is properly set
        if not student.password:
            student.password = 'student123'
            student.save()
            print("✅ Fixed missing password")
        
        # Check user account
        if not student.user:
            User = get_user_model()
            user = User.objects.create_user(
                email=f"student_{student.student_id}@school.edu",
                password=student.password,
                first_name=student.first_name,
                last_name=student.last_name
            )
            if hasattr(user, 'role'):
                user.role = 'STUDENT'
                user.save()
            student.user = user
            student.save()
            print("✅ Created missing user account")
        else:
            print(f"✅ User account exists: {student.user.email}")
        
        print("\n=== STUDENT LOGIN FIXED ===")
        return True
        
    except Student.DoesNotExist:
        print("❌ Student 2025BASIC_9001 not found")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    fix_student_login()