#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from teachers.models import Teacher
from schools.models import Class

User = get_user_model()

def test_teacher_classes():
    print("=== Testing Teacher Class Assignments ===")
    
    # Find ADOMAH JACKLINE
    try:
        user = User.objects.get(first_name__icontains='ADOMAH', last_name__icontains='JACKLINE')
        print(f"Found user: {user.get_full_name()} (ID: {user.id}, Email: {user.email})")
        
        # Get teacher profile
        try:
            teacher = Teacher.objects.get(user=user)
            print(f"Teacher profile: {teacher} (ID: {teacher.id})")
            
            # Check assigned classes
            assigned_classes = teacher.get_assigned_classes()
            print(f"Assigned classes count: {assigned_classes.count()}")
            
            for cls in assigned_classes:
                print(f"  - Class: {cls} (ID: {cls.id})")
                print(f"    Class teacher: {cls.class_teacher}")
                print(f"    Students: {cls.students.filter(is_active=True).count()}")
            
            # Check all classes where this user is class teacher
            all_classes = Class.objects.filter(class_teacher=user)
            print(f"\nDirect query - Classes where user is class_teacher: {all_classes.count()}")
            for cls in all_classes:
                print(f"  - {cls} (ID: {cls.id})")
                
        except Teacher.DoesNotExist:
            print("Teacher profile not found!")
            
    except User.DoesNotExist:
        print("User ADOMAH JACKLINE not found!")
        
        # List all users with similar names
        users = User.objects.filter(first_name__icontains='ADOMAH')
        print(f"Found {users.count()} users with 'ADOMAH' in first name:")
        for u in users:
            print(f"  - {u.get_full_name()} ({u.email})")

if __name__ == "__main__":
    test_teacher_classes()