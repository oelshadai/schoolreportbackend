#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student

print('Checking student passwords...')
students = Student.objects.all()

for student in students:
    print(f'Student ID: {student.student_id}')
    print(f'Name: {student.first_name} {student.last_name}')
    if hasattr(student, 'password') and student.password:
        print(f'Password: {student.password}')
    else:
        print('No password set')
    print('---')