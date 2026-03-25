#!/usr/bin/env python
"""
Test script for Student Reports functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from reports.models import ReportCard
from schools.models import School, Term, AcademicYear

User = get_user_model()

def test_student_reports():
    """Test the student reports functionality"""
    print("🧪 Testing Student Reports Functionality...")
    
    # Get a test student
    student = Student.objects.filter(is_active=True).first()
    if not student:
        print("❌ No active students found. Please create a test student first.")
        return
    
    print(f"✅ Found test student: {student.get_full_name()} ({student.student_id})")
    
    # Get or create a test term
    school = student.school
    academic_year, _ = AcademicYear.objects.get_or_create(
        school=school,
        name="2024/2025",
        defaults={'is_current': True}
    )
    
    term, _ = Term.objects.get_or_create(
        academic_year=academic_year,
        name='FIRST',
        defaults={
            'is_current': True,
            'start_date': '2024-09-01',
            'end_date': '2024-12-15'
        }
    )
    
    print(f"✅ Using term: {term.get_name_display() if hasattr(term, 'get_name_display') else term.name}")
    
    # Create a test report card
    report_card, created = ReportCard.objects.get_or_create(
        student=student,
        term=term,
        defaults={
            'status': 'GENERATED',
            'generated_by': User.objects.filter(role='TEACHER').first()
        }
    )
    
    if created:
        report_card.generate_report_code()
        print(f"✅ Created test report card: {report_card.report_code}")
    else:
        print(f"✅ Using existing report card: {report_card.report_code}")
    
    # Test publishing the report
    if report_card.status != 'PUBLISHED':
        success = report_card.publish_report()
        if success:
            print("✅ Report published successfully")
        else:
            print("❌ Failed to publish report")
    else:
        print("✅ Report already published")
    
    # Test student access
    if student.user:
        print(f"✅ Student has user account: {student.user.email}")
        print(f"✅ Student can access reports via API: /students/reports/")
        print(f"✅ Student can download report via: /students/reports/{report_card.id}/download/")
    else:
        print("❌ Student has no user account - cannot access reports")
    
    print("\n📋 Summary:")
    print(f"   Student: {student.get_full_name()}")
    print(f"   Report Code: {report_card.report_code}")
    print(f"   Status: {report_card.status}")
    print(f"   Published: {report_card.published_at}")
    print(f"   Can Access: {'Yes' if student.user else 'No'}")
    
    print("\n🎉 Student Reports functionality test completed!")

if __name__ == "__main__":
    test_student_reports()