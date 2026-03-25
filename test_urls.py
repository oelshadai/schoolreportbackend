#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

# Test URL resolution
try:
    url = reverse('assignment-publish', kwargs={'pk': 1})
    print(f"Publish URL resolved: {url}")
except Exception as e:
    print(f"URL resolution failed: {e}")

# Test client access
client = Client()
try:
    response = client.get('/api/assignments/')
    print(f"Assignment list endpoint status: {response.status_code}")
except Exception as e:
    print(f"Assignment list endpoint failed: {e}")

# Check if publish action exists
from assignments.views import AssignmentViewSet
actions = [method for method in dir(AssignmentViewSet) if not method.startswith('_')]
print(f"AssignmentViewSet methods: {[a for a in actions if 'publish' in a.lower()]}")

# Check router registration
from assignments.urls import router
print(f"Router registered viewsets: {list(router.registry)}")