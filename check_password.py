#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from django.contrib.auth.hashers import check_password

print('Checking password for user 2025BASIC_9001...')
student = Student.objects.filter(student_id='2025BASIC_9001').first()

if student:
    print(f'Student found: {student.student_id}')
    
    # Test common passwords
    test_passwords = ['bs9test', 'password', '123456', '2025BASIC_9001', 'charity', 'bonsu']
    
    for pwd in test_passwords:
        if hasattr(student, 'password') and student.password:
            # Check if it's a hashed password
            if student.password.startswith('pbkdf2_') or student.password.startswith('$'):
                is_correct = check_password(pwd, student.password)
            else:
                # Plain text comparison
                is_correct = student.password == pwd
            
            if is_correct:
                print(f'✓ Password found: {pwd}')
                break
    else:
        print('Password not found in common list')
        if hasattr(student, 'password'):
            print(f'Password hash: {student.password[:50]}...')
        else:
            print('No password field')
else:
    print('User not found')