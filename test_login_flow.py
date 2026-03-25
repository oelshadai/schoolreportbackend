#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from rest_framework_simplejwt.tokens import RefreshToken

# Test the login flow manually
student = Student.objects.get(student_id='BS9001')
print(f'Student: {student}')
print(f'User: {student.user}')
print(f'Password plain: {student.password}')
print(f'Password match: {student.user.check_password("bs9test")}')

try:
    refresh = RefreshToken.for_user(student.user)
    print(f'Token generated: SUCCESS')
    print(f'Access: {str(refresh.access_token)}')
    print()
    print('Response would be:')
    print({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': student.user.id,
            'email': student.user.email,
            'first_name': student.user.first_name or '',
            'last_name': student.user.last_name or '',
            'role': 'STUDENT'
        }
    })
except Exception as e:
    import traceback
    print(f'Token generation FAILED: {e}')
    traceback.print_exc()
