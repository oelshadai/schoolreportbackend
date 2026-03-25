#!/usr/bin/env python3
"""
URL Debug Script - Test URL patterns and endpoint configuration
"""
import os
import sys
import django
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.test import Client

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

def test_url_patterns():
    """Test URL patterns and endpoints"""
    print("=== URL Pattern Debug Test ===\n")
    
    # Test basic URL patterns
    url_tests = [
        ('students-list', '/api/students/'),
        ('classes-list', '/api/classes/'),
        ('subjects-list', '/api/subjects/'),
        ('teachers-list', '/api/teachers/'),
        ('behavior-list', '/api/behavior/'),
        ('behavior-detail', '/api/behavior/1/', {'pk': 1}),
    ]
    
    print("1. Testing URL Reverse Resolution:")
    for name, expected_url, kwargs in [(t[0], t[1], t[2] if len(t) > 2 else {}) for t in url_tests]:
        try:
            resolved_url = reverse(name, kwargs=kwargs)
            status = "✓ PASS" if resolved_url == expected_url else f"✗ FAIL (got: {resolved_url})"
            print(f"   {name}: {status}")
        except NoReverseMatch as e:
            print(f"   {name}: ✗ FAIL - {e}")
    
    print("\n2. Testing Endpoint Accessibility:")
    client = Client()
    
    endpoints = [
        ('GET', '/api/students/'),
        ('GET', '/api/classes/'),
        ('GET', '/api/subjects/'),
        ('GET', '/api/teachers/'),
        ('GET', '/api/behavior/'),
        ('POST', '/api/behavior/'),
    ]
    
    for method, url in endpoints:
        try:
            if method == 'GET':
                response = client.get(url)
            elif method == 'POST':
                response = client.post(url, {'student': 1, 'behavior_type': 'positive', 'description': 'test'})
            
            print(f"   {method} {url}: Status {response.status_code}")
        except Exception as e:
            print(f"   {method} {url}: ✗ ERROR - {e}")

def check_behavior_model():
    """Check behavior model and data"""
    print("\n3. Testing Behavior Model:")
    try:
        from api.models import BehaviorRecord, Student
        
        # Check if model exists
        print(f"   BehaviorRecord model: ✓ EXISTS")
        print(f"   Fields: {[f.name for f in BehaviorRecord._meta.fields]}")
        
        # Check existing records
        count = BehaviorRecord.objects.count()
        print(f"   Existing records: {count}")
        
        # Check students for testing
        student_count = Student.objects.count()
        print(f"   Available students: {student_count}")
        
    except ImportError as e:
        print(f"   ✗ IMPORT ERROR - {e}")
    except Exception as e:
        print(f"   ✗ ERROR - {e}")

def check_urls_configuration():
    """Check URLs configuration"""
    print("\n4. Checking URLs Configuration:")
    try:
        from django.urls import get_resolver
        from school_management.urls import urlpatterns as main_patterns
        
        print(f"   Main URL patterns: {len(main_patterns)}")
        
        # Check if api URLs are included
        api_included = any('api/' in str(pattern.pattern) for pattern in main_patterns)
        print(f"   API URLs included: {'✓ YES' if api_included else '✗ NO'}")
        
        # Get all URL patterns
        resolver = get_resolver()
        url_patterns = []
        
        def extract_patterns(patterns, prefix=''):
            for pattern in patterns:
                if hasattr(pattern, 'url_patterns'):
                    extract_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
                else:
                    url_patterns.append(prefix + str(pattern.pattern))
        
        extract_patterns(resolver.url_patterns)
        
        # Check for behavior URLs
        behavior_urls = [url for url in url_patterns if 'behavior' in url.lower()]
        print(f"   Behavior URLs found: {len(behavior_urls)}")
        for url in behavior_urls:
            print(f"     - {url}")
            
    except Exception as e:
        print(f"   ✗ ERROR - {e}")

if __name__ == '__main__':
    test_url_patterns()
    check_behavior_model()
    check_urls_configuration()
    print("\n=== Debug Test Complete ===")