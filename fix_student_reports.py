#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from django.db import transaction
from students.models import Student
from reports.models import ReportCard

def create_student_accounts():
    """Create User accounts for all students who don't have them"""
    print("=== CREATING STUDENT USER ACCOUNTS ===")
    
    # Get or create Students group
    students_group, created = Group.objects.get_or_create(name='Students')
    if created:
        print("✓ Created Students group")
    
    # Get all students without user accounts
    students_without_users = Student.objects.filter(user__isnull=True)
    print(f"Found {students_without_users.count()} students without User accounts")
    
    if students_without_users.count() == 0:
        print("All students already have User accounts!")
        return
    
    created_count = 0
    
    with transaction.atomic():
        for student in students_without_users:
            try:
                # Create username from student details
                username = f"{student.student_id}_{student.first_name.lower()}"
                
                # Check if username already exists
                if User.objects.filter(username=username).exists():
                    username = f"{student.student_id}_{student.first_name.lower()}_{student.last_name.lower()}"
                
                if User.objects.filter(username=username).exists():
                    username = f"student_{student.id}_{student.student_id}"
                
                # Create user account
                user = User.objects.create(
                    username=username,
                    email=student.email or f"{username}@school.com",
                    first_name=student.first_name,
                    last_name=student.last_name,
                    password=make_password('student123'),  # Default password
                    is_active=True
                )
                
                # Add to Students group
                user.groups.add(students_group)
                
                # Link to student
                student.user = user
                student.save()
                
                print(f"✓ Created account for {student.first_name} {student.last_name} (username: {username})")
                created_count += 1
                
            except Exception as e:
                print(f"✗ Failed to create account for {student.first_name} {student.last_name}: {e}")
    
    print(f"✓ Successfully created {created_count} student accounts")

def test_student_reports_api():
    """Test the student reports API for each student"""
    print("\n=== TESTING STUDENT REPORTS API ===")
    
    students_with_users = Student.objects.filter(user__isnull=False)
    print(f"Testing API for {students_with_users.count()} students with User accounts")
    
    for student in students_with_users:
        print(f"\nTesting for student: {student.first_name} {student.last_name}")
        print(f"  Username: {student.user.username}")
        print(f"  User ID: {student.user.id}")
        print(f"  Student ID: {student.id}")
        
        # Check published reports for this student
        published_reports = ReportCard.objects.filter(
            student=student,
            status='PUBLISHED'
        )
        print(f"  Published reports: {published_reports.count()}")
        
        for report in published_reports:
            print(f"    - {report.term.get_name_display()} ({report.status}) - Published: {report.published_at}")

def main():
    print("=== FIXING STUDENT REPORT ACCESS ===\n")
    
    # Step 1: Create missing user accounts
    create_student_accounts()
    
    # Step 2: Test the API
    test_student_reports_api()
    
    print("\n=== SUMMARY ===")
    print("If students still can't access reports:")
    print("1. Check that the student is logging in with their correct username")
    print("2. Default password is 'student123' (should be changed)")
    print("3. Make sure the frontend is calling /students/published-reports/ correctly")
    print("4. Check browser console for any CORS or authentication errors")

if __name__ == "__main__":
    main()