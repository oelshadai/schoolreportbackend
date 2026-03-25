#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from django.contrib.auth.models import Group
from django.db import transaction
from students.models import Student
from reports.models import ReportCard

def fix_student_authentication():
    """Fix student authentication and group membership"""
    print("=== FIXING STUDENT AUTHENTICATION ===")
    
    # Get or create Students group
    students_group, created = Group.objects.get_or_create(name='Students')
    if created:
        print("✓ Created Students group")
    
    # Get all students with published reports
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    print(f"\n📊 Students with published reports: {students_with_reports.count()}")
    
    for student in students_with_reports:
        print(f"\n🎓 {student.first_name} {student.last_name}")
        print(f"   🆔 Student ID: {student.student_id}")
        
        if student.user:
            user = student.user
            print(f"   📧 Login Email: {user.email}")
            print(f"   👤 Role: {user.role}")
            print(f"   ✅ Active: {user.is_active}")
            
            # Fix role if needed
            if user.role != 'STUDENT':
                user.role = 'STUDENT'
                user.save()
                print(f"   🔧 Fixed role to STUDENT")
            
            # Add to Students group if needed
            if students_group not in user.groups.all():
                user.groups.add(students_group)
                print(f"   👥 Added to Students group")
            else:
                print(f"   ✅ Already in Students group")
            
            # Show published reports
            reports = ReportCard.objects.filter(student=student, status='PUBLISHED')
            print(f"   📊 Published reports: {reports.count()}")
            for report in reports:
                print(f"       - {report.term.get_name_display()} (Published: {report.published_at.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print(f"   ❌ No User account linked!")
    
    print("\n=== TESTING STUDENT AUTHENTICATION ===")
    
    # Test the student authentication requirements
    student_users = User.objects.filter(role='STUDENT', groups__name='Students')
    print(f"Student users with correct role and group: {student_users.count()}")
    
    for user in student_users:
        try:
            student = Student.objects.get(user=user)
            reports = ReportCard.objects.filter(student=student, status='PUBLISHED')
            print(f"✅ {user.email} → {student.first_name} {student.last_name} → {reports.count()} published reports")
        except Student.DoesNotExist:
            print(f"⚠️ {user.email} → No linked Student record")
    
    print(f"\n=== STUDENT LOGIN INSTRUCTIONS ===")
    for student in students_with_reports:
        if student.user:
            print(f"👤 {student.first_name} {student.last_name}")
            print(f"   📧 Email: {student.user.email}")
            print(f"   🔑 Password: (use their actual password)")
            print(f"   🔗 URL: http://localhost:8080/student/reports")
            print()

if __name__ == "__main__":
    fix_student_authentication()