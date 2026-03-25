#!/usr/bin/env python
"""
Reset teacher password for testing
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from teachers.models import Teacher

def reset_teacher_password():
    """Reset teacher password for testing"""
    
    try:
        # Get first teacher
        teacher = Teacher.objects.first()
        if not teacher:
            print("❌ No teachers found")
            return
        
        user = teacher.user
        print(f"Resetting password for teacher: {user.email}")
        
        # Set simple password for testing
        new_password = "password123"
        user.set_password(new_password)
        user.save()
        
        print(f"✅ Password reset successful!")
        print(f"Email: {user.email}")
        print(f"Password: {new_password}")
        print(f"Role: {user.role}")
        print(f"School: {user.school.name if user.school else 'No school'}")
        
        # Also check if user is active
        if not user.is_active:
            user.is_active = True
            user.save()
            print("✅ User activated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    reset_teacher_password()