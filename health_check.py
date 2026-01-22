#!/usr/bin/env python3
"""
Simple health check script for the Django backend
"""
import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

def check_health():
    """Check if the Django application is healthy"""
    try:
        from django.db import connection
        from django.core.management import execute_from_command_line
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            
        print("✅ Database connection: OK")
        print("✅ Django application: OK")
        print("✅ Health check: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = check_health()
    sys.exit(0 if success else 1)