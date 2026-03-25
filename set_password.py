#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User

try:
    user = User.objects.get(email='admin@example.com')
    user.set_password('admin123')
    user.save()
    print('Password set successfully for admin@example.com')
except User.DoesNotExist:
    print('User not found')
except Exception as e:
    print(f'Error: {e}')