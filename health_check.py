#!/usr/bin/env python3
"""
Simple health check script for the Django application
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

def check_database():
    """Check database connectivity"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ Database connection: OK")
        return True
    except Exception as e:
        print(f"✗ Database connection: FAILED - {e}")
        return False

def check_settings():
    """Check critical settings"""
    try:
        print(f"✓ DEBUG: {settings.DEBUG}")
        print(f"✓ ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        print(f"✓ CORS_ALLOW_ALL_ORIGINS: {settings.CORS_ALLOW_ALL_ORIGINS}")
        print(f"✓ DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
        return True
    except Exception as e:
        print(f"✗ Settings check: FAILED - {e}")
        return False

def check_apps():
    """Check if all apps are properly installed"""
    try:
        from django.apps import apps
        app_configs = apps.get_app_configs()
        print(f"✓ Installed apps: {len(app_configs)} apps loaded")
        return True
    except Exception as e:
        print(f"✗ Apps check: FAILED - {e}")
        return False

if __name__ == "__main__":
    print("=== Django Health Check ===")
    
    checks = [
        check_settings,
        check_database,
        check_apps,
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 All health checks passed!")
        sys.exit(0)
    else:
        print("❌ Some health checks failed!")
        sys.exit(1)