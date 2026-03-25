#!/usr/bin/env python3
"""
Create a test student with proper authentication setup
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from schools.models import School, Class, AcademicYear, Term
from datetime import date, datetime

User = get_user_model()

def create_test_student():
    """Create a test student with proper authentication"""
    
    # Get or create school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'address': 'Test Address',
            'phone': '1234567890',
            'email': 'test@school.com',
            'subscription_plan': 'BASIC'
        }
    )
    print(f"School: {school.name} ({'created' if created else 'exists'})")
    
    # Get or create academic year
    current_year = datetime.now().year
    academic_year, created = AcademicYear.objects.get_or_create(
        school=school,
        year=current_year,
        defaults={
            'start_date': date(current_year, 9, 1),
            'end_date': date(current_year + 1, 7, 31),
            'is_current': True
        }
    )
    print(f"Academic Year: {academic_year.year} ({'created' if created else 'exists'})")
    
    # Get or create class
    test_class, created = Class.objects.get_or_create(
        school=school,
        level="Grade 10A",
        defaults={
            'academic_year': academic_year,
            'capacity': 30
        }
    )
    print(f"Class: {test_class.level} ({'created' if created else 'exists'})")
    
    # Create test student
    student_id = "STD001"
    
    # Delete existing student if exists
    Student.objects.filter(student_id=student_id).delete()
    User.objects.filter(email=f"std_{student_id}@testschool.edu").delete()
    
    # Create new student
    student = Student.objects.create(
        school=school,
        student_id=student_id,
        first_name="Test",
        last_name="Student",
        gender="M",
        date_of_birth=date(2005, 1, 1),
        current_class=test_class,
        guardian_name="Test Guardian",
        guardian_phone="1234567890",
        guardian_address="Test Address",
        admission_date=date.today(),
        username=f"std_{student_id}",
        password="password123"  # Simple password for testing
    )
    
    print(f"✅ Created student: {student.get_full_name()}")
    print(f"   Student ID: {student.student_id}")
    print(f"   Username: {student.username}")
    print(f"   Password: {student.password}")
    print(f"   User Account: {student.user.email if student.user else 'None'}")
    print(f"   User Role: {student.user.role if student.user else 'None'}")
    
    # Test login credentials
    if student.user:
        print(f"\n🔐 Login Test:")
        print(f"   Email: {student.user.email}")
        print(f"   Student ID: {student.student_id}")
        print(f"   Password: {student.password}")
        print(f"   Django User ID: {student.user.id}")
        print(f"   Django User Active: {student.user.is_active}")
    
    return student

if __name__ == "__main__":
    print("Creating test student for authentication testing...")
    student = create_test_student()
    print(f"\n✅ Test student created successfully!")
    print(f"Use Student ID: {student.student_id} and Password: {student.password} to login")