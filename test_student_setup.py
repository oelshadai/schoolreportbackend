#!/usr/bin/env python
import os
import sys
import django

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from accounts.models import User

def main():
    print("=== Student Login Debug ===")
    
    # Check existing students
    students = Student.objects.all()
    print(f"Total students in database: {students.count()}")
    
    if students.exists():
        for student in students[:5]:
            print(f"Student ID: {student.student_id}, Name: {student.get_full_name()}, Has User: {bool(student.user)}")
    
    # Create a test student if none exist
    if not students.exists():
        print("Creating test student...")
        try:
            student = Student.objects.create(
                student_id="TEST001",
                first_name="Test",
                last_name="Student",
                password="password123"
            )
            print(f"Created test student: {student.student_id}")
        except Exception as e:
            print(f"Error creating test student: {e}")
    
    # Test login credentials
    test_student = students.first()
    if test_student:
        print(f"\nTest with: student_id='{test_student.student_id}', password='password123'")

if __name__ == "__main__":
    main()