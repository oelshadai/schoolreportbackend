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
from students.portal_views import student_published_reports
from django.test import RequestFactory
import json

def test_student_reports_api():
    """Test the student published reports API"""
    print("=== TESTING STUDENT REPORTS API ===")
    
    # Get students with published reports
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    print(f"Students with published reports: {students_with_reports.count()}")
    
    for student in students_with_reports:
        print(f"\n🎓 Testing student: {student.first_name} {student.last_name}")
        print(f"   Student ID: {student.id}")
        print(f"   Has user account: {student.user is not None}")
        
        if not student.user:
            print("   ❌ No user account - skipping")
            continue
        
        print(f"   User email: {student.user.email}")
        print(f"   User role: {student.user.role}")
        print(f"   User active: {student.user.is_active}")
        
        # Test the API function directly
        try:
            factory = RequestFactory()
            request = factory.get('/students/published-reports/')
            request.user = student.user
            
            # Call the API function
            response = student_published_reports(request)
            
            print(f"   ✅ API Response Status: {response.status_code}")
            
            if hasattr(response, 'data'):
                print(f"   📊 Number of reports returned: {len(response.data) if response.data else 0}")
                
                if response.data:
                    print("   📄 Report details:")
                    for i, report in enumerate(response.data[:2]):  # Show first 2
                        print(f"      {i+1}. {report.get('term_name', 'N/A')} - {report.get('academic_year', 'N/A')}")
                        print(f"         Status: {report.get('status', 'N/A')}")
                        print(f"         Published: {report.get('published_at', 'N/A')}")
                        if report.get('pdf_url'):
                            print(f"         PDF URL: {report['pdf_url']}")
                else:
                    print("   ⚠️ No reports in response data")
            else:
                print(f"   ⚠️ No data attribute in response")
                
        except Exception as e:
            print(f"   ❌ API Error: {e}")
    
    # Also test what reports exist in the database
    print(f"\n=== DATABASE REPORTS ===")
    published_reports = ReportCard.objects.filter(status='PUBLISHED')
    print(f"Total published reports in database: {published_reports.count()}")
    
    for report in published_reports:
        print(f"📊 Report ID {report.id}:")
        print(f"   Student: {report.student.first_name} {report.student.last_name}")
        print(f"   Term: {report.term.get_name_display()}")
        print(f"   Status: {report.status}")
        print(f"   Published: {report.published_at}")
        print(f"   PDF file: {report.pdf_file}")

if __name__ == "__main__":
    test_student_reports_api()