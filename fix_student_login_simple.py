#!/usr/bin/env python3
"""
Fix Windows-specific issues in student login - Windows compatible version
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
        print(f"Current password: {student.password}")
        
        # The password is hashed, but we need plain text for student login
        # Set the correct plain text password
        student.password = 'student123'
        student.save()
        print("[OK] Fixed password - set to plain text")
        
        # Check user account
        if not student.user:
            User = get_user_model()
            user = User.objects.create_user(
                email=f"student_{student.student_id}@school.edu",
                password='student123',
                first_name=student.first_name,
                last_name=student.last_name
            )
            if hasattr(user, 'role'):
                user.role = 'STUDENT'
                user.save()
            student.user = user
            student.save()
            print("[OK] Created missing user account")
        else:
            print(f"[OK] User account exists: {student.user.email}")
            # Make sure user password is correct
            student.user.set_password('student123')
            student.user.save()
            print("[OK] Updated user password")
        
        print("\n=== STUDENT LOGIN FIXED ===")
        print("Student can now login with:")
        print("Username: 2025BASIC_9001")
        print("Password: student123")
        return True
        
    except Student.DoesNotExist:
        print("[ERROR] Student 2025BASIC_9001 not found")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return False

if __name__ == '__main__':
    fix_student_login()