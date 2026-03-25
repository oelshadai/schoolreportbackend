#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student

students = Student.objects.all()[:4]
for s in students:
    print(f"{s.student_id}:")
    print(f"  full_name: {s.get_full_name()}")
    print(f"  plain password: {s.password}")
    print(f"  user: {s.user}")
    print(f"  user password hash: {s.user.password if s.user else 'N/A'}")
    print()
