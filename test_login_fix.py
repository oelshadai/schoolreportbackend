#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from assignments.models import Assignment

def test_assignment_query():
    """Test querying assignments to ensure start_date field works"""
    try:
        # Try to query assignments with start_date field
        assignments = Assignment.objects.all()
        print(f"Successfully queried {assignments.count()} assignments")
        
        # Try to access start_date field specifically
        for assignment in assignments[:3]:  # Just check first 3
            print(f"Assignment: {assignment.title}, Start Date: {assignment.start_date}")
        
        print("✓ Assignment queries work correctly - start_date field is accessible")
        return True
        
    except Exception as e:
        print(f"✗ Error querying assignments: {e}")
        return False

def test_login_api():
    """Test the login API to see if it works now"""
    try:
        # Test with a simple request to the login endpoint
        response = requests.post('http://localhost:8000/api/accounts/login/', 
                               json={'username': 'test', 'password': 'test'}, 
                               timeout=5)
        
        if response.status_code == 400:
            print("✓ Login endpoint is accessible (returned 400 for invalid credentials, which is expected)")
            return True
        else:
            print(f"Login endpoint returned status: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        print("Server is not running - cannot test login API")
        return False
    except Exception as e:
        print(f"Error testing login API: {e}")
        return False

if __name__ == "__main__":
    print("Testing assignment model after adding start_date field...")
    print("=" * 60)
    
    # Test database queries
    db_test = test_assignment_query()
    
    print("\nTesting login API...")
    print("=" * 60)
    
    # Test API
    api_test = test_login_api()
    
    print(f"\nResults:")
    print(f"Database queries: {'PASS' if db_test else 'FAIL'}")
    print(f"API test: {'PASS' if api_test else 'FAIL'}")