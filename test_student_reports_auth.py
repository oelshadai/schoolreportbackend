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
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, force_authenticate
from students.portal_views import student_published_reports

def test_student_reports_with_auth():
    """Test student reports API with proper authentication"""
    print("=== TESTING STUDENT REPORTS WITH AUTHENTICATION ===")
    
    # Get students with published reports
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    for student in students_with_reports:
        print(f"\n🎓 Testing student: {student.first_name} {student.last_name}")
        
        if not student.user:
            print("   ❌ No user account")
            continue
            
        user = student.user
        print(f"   📧 Email: {user.email}")
        print(f"   🔑 Role: {user.role}")
        print(f"   ✅ Active: {user.is_active}")
        
        # Test with proper DRF authentication
        factory = APIRequestFactory()
        request = factory.get('/students/published-reports/')
        
        # Force authenticate the request
        force_authenticate(request, user=user)
        
        try:
            # Call the API function with authenticated request
            response = student_published_reports(request)
            
            print(f"   ✅ API Status: {response.status_code}")
            
            if response.status_code == 200 and hasattr(response, 'data'):
                reports_data = response.data
                print(f"   📊 Reports returned: {len(reports_data)}")
                
                if reports_data:
                    for i, report in enumerate(reports_data):
                        print(f"      {i+1}. Term: {report.get('term_name')}")
                        print(f"         Academic Year: {report.get('academic_year')}")
                        print(f"         Status: {report.get('status')}")
                        print(f"         Published: {report.get('published_at')}")
                else:
                    print("   ⚠️ No reports returned")
                    
            else:
                print(f"   ❌ API Error: {response.status_code}")
                if hasattr(response, 'data'):
                    print(f"      Error data: {response.data}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n=== CHECKING STUDENT USERS ===")
    student_users = User.objects.filter(role='STUDENT', is_active=True)
    print(f"Active student users: {student_users.count()}")
    
    for user in student_users:
        try:
            student = Student.objects.get(user=user)
            reports_count = ReportCard.objects.filter(student=student, status='PUBLISHED').count()
            print(f"👤 {user.email} → {student.first_name} {student.last_name} → {reports_count} reports")
        except Student.DoesNotExist:
            print(f"👤 {user.email} → ❌ No Student record")

def fix_student_report_access():
    """Create a comprehensive fix for student report access"""
    print(f"\n=== FIXING STUDENT REPORT ACCESS ===")
    
    # Step 1: Ensure students have STUDENT role
    students_with_users = Student.objects.filter(user__isnull=False)
    fixed_roles = 0
    
    for student in students_with_users:
        if student.user.role != 'STUDENT':
            student.user.role = 'STUDENT'
            student.user.save()
            fixed_roles += 1
            print(f"✓ Fixed role for {student.first_name} {student.last_name}")
    
    print(f"Fixed {fixed_roles} user roles")
    
    # Step 2: Test the fixed setup
    print(f"\n=== VERIFICATION ===")
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    for student in students_with_reports:
        reports = ReportCard.objects.filter(student=student, status='PUBLISHED')
        print(f"🎓 {student.first_name} {student.last_name}:")
        print(f"   Email: {student.user.email if student.user else 'No User'}")
        print(f"   Role: {student.user.role if student.user else 'N/A'}")
        print(f"   Published reports: {reports.count()}")
        
        if reports.exists():
            for report in reports:
                print(f"      - {report.term.get_name_display()} (Published: {report.published_at.strftime('%Y-%m-%d %H:%M')})")

if __name__ == "__main__":
    test_student_reports_with_auth()
    fix_student_report_access()