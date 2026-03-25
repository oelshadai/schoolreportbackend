#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from students.models import Student  
from reports.models import ReportCard
from django.contrib.auth import authenticate

def test_student_id_login():
    """Test student login using student ID"""
    print("=== TESTING STUDENT ID LOGIN ===")
    
    # Get students with published reports
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    for student in students_with_reports:
        print(f"\n🎓 Student: {student.first_name} {student.last_name}")
        print(f"   📝 Student ID: {student.student_id}")
        
        if student.user:
            user = student.user
            print(f"   📧 User Email: {user.email}")
            print(f"   👤 Username: {user.username if hasattr(user, 'username') else 'No username field'}")
            print(f"   🔑 Role: {user.role}")
            print(f"   ✅ Active: {user.is_active}")
            
            # Check if the student can authenticate with their student ID
            # First, let's see what authentication backends are configured
            from django.conf import settings
            print(f"   🔐 Auth backends: {settings.AUTHENTICATION_BACKENDS}")
            
            # Test authentication with student ID 
            try:
                # Try authenticating with student ID as username
                auth_user = authenticate(username=student.student_id, password='student123')
                if auth_user:
                    print(f"   ✅ Can authenticate with student ID: {student.student_id}")
                else:
                    print(f"   ❌ Cannot authenticate with student ID: {student.student_id}")
            except Exception as e:
                print(f"   ❌ Auth error: {e}")
                
            # Test authentication with email
            try:
                auth_user = authenticate(username=user.email, password='student123')
                if auth_user:
                    print(f"   ✅ Can authenticate with email: {user.email}")
                else:
                    print(f"   ❌ Cannot authenticate with email: {user.email}")
            except Exception as e:
                print(f"   ❌ Email auth error: {e}")
                
        else:
            print(f"   ❌ No User account linked!")
    
    print(f"\n=== CHECKING STUDENT LOGIN SETUP ===")
    
    # Check if students have username field set to their student ID
    students = Student.objects.filter(user__isnull=False)
    for student in students[:5]:  # Check first 5
        print(f"Student {student.student_id}:")
        if hasattr(student.user, 'username'):
            print(f"   Username: {student.user.username}")
        print(f"   Email: {student.user.email}")
        print(f"   Expected login: {student.student_id}")
        
        # Check if username matches student ID
        if hasattr(student.user, 'username') and student.user.username == student.student_id:
            print(f"   ✅ Username matches student ID")
        else:
            print(f"   ⚠️ Username doesn't match student ID")

def fix_student_login_usernames():
    """Fix student usernames to match their student IDs"""
    print(f"\n=== FIXING STUDENT LOGIN USERNAMES ===")
    
    students = Student.objects.filter(user__isnull=False)
    fixed_count = 0
    
    for student in students:
        if hasattr(student.user, 'username'):
            if student.user.username != student.student_id:
                old_username = student.user.username
                student.user.username = student.student_id
                student.user.save()
                print(f"✓ Fixed {student.first_name} {student.last_name}: {old_username} → {student.student_id}")
                fixed_count += 1
            else:
                print(f"- {student.first_name} {student.last_name}: Already correct ({student.student_id})")
        else:
            print(f"⚠️ {student.first_name} {student.last_name}: No username field")
    
    print(f"\n✅ Fixed {fixed_count} student usernames")
    
    # Test after fix
    print(f"\n=== VERIFICATION AFTER FIX ===")
    for student in Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    ):
        if student.user and hasattr(student.user, 'username'):
            print(f"🎓 {student.first_name} {student.last_name}")
            print(f"   Login with: {student.user.username} (should be {student.student_id})")
            print(f"   Password: student123 (if not changed)")

if __name__ == "__main__":
    test_student_id_login()
    fix_student_login_usernames()