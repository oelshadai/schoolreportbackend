#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.db import transaction
from students.models import Student

def fix_student_groups():
    """Add all students to the Students group"""
    print("=== FIXING STUDENT GROUP MEMBERSHIP ===")
    
    # Get or create Students group
    students_group, created = Group.objects.get_or_create(name='Students')
    if created:
        print("✓ Created Students group")
    
    # Get all students with linked User accounts
    students_with_users = Student.objects.filter(user__isnull=False)
    print(f"Found {students_with_users.count()} students with User accounts")
    
    fixed_count = 0
    
    with transaction.atomic():
        for student in students_with_users:
            if students_group not in student.user.groups.all():
                student.user.groups.add(students_group)
                print(f"✓ Added {student.first_name} {student.last_name} (username: {student.user.username}) to Students group")
                fixed_count += 1
            else:
                print(f"- {student.first_name} {student.last_name} already in Students group")
    
    print(f"\n✅ Fixed {fixed_count} student group memberships")
    
    # Verify the fix
    print("\n=== VERIFICATION ===")
    students_in_group = User.objects.filter(groups__name='Students')
    print(f"Total users in Students group: {students_in_group.count()}")
    
    for user in students_in_group:
        try:
            student = Student.objects.get(user=user)
            print(f"✓ {user.username} → {student.first_name} {student.last_name}")
        except Student.DoesNotExist:
            print(f"⚠️ {user.username} → No linked Student record")

if __name__ == "__main__":
    fix_student_groups()