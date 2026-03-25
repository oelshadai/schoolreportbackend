#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from django.contrib.auth.models import User, Group
from students.models import Student
from teachers.models import Teacher
from reports.models import ReportCard

def debug_student_auth():
    print("=== DEBUGGING STUDENT AUTHENTICATION ===")
    
    # Check Students group
    try:
        students_group = Group.objects.get(name='Students')
        print(f"✓ Students group exists with {students_group.user_set.count()} users")
    except Group.DoesNotExist:
        print("✗ Students group doesn't exist!")
        return
    
    # Check all students and their accounts
    students = Student.objects.all()
    print(f"\n=== STUDENT ACCOUNTS ({students.count()} total) ===")
    
    for student in students:
        print(f"\nStudent: {student.first_name} {student.last_name} (ID: {student.student_id})")
        print(f"  Email: {student.email}")
        
        if student.user:
            print(f"  ✓ Has User account: {student.user.username}")
            print(f"  ✓ User is active: {student.user.is_active}")
            print(f"  ✓ Groups: {[g.name for g in student.user.groups.all()]}")
            print(f"  ✓ In Students group: {students_group in student.user.groups.all()}")
        else:
            print("  ✗ No linked User account!")
    
    # Check published reports for students
    published_reports = ReportCard.objects.filter(status='PUBLISHED')
    print(f"\n=== PUBLISHED REPORTS ({published_reports.count()} total) ===")
    
    for report in published_reports:
        print(f"Report for: {report.student.first_name} {report.student.last_name}")
        print(f"  Student has user: {report.student.user is not None}")
        if report.student.user:
            print(f"  Student username: {report.student.user.username}")
            print(f"  In Students group: {students_group in report.student.user.groups.all()}")
    
    # Test student authentication flow
    print(f"\n=== TESTING AUTHENTICATION FLOW ===")
    user_students = User.objects.filter(groups__name='Students')
    print(f"Users in Students group: {user_students.count()}")
    
    for user in user_students:
        try:
            student = Student.objects.get(user=user)
            reports = ReportCard.objects.filter(student=student, status='PUBLISHED')
            print(f"User {user.username} -> Student {student.first_name} {student.last_name} -> {reports.count()} published reports")
        except Student.DoesNotExist:
            print(f"User {user.username} has no linked Student record!")

if __name__ == "__main__":
    debug_student_auth()