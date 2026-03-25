#!/usr/bin/env python
"""
API Test Script for ReportLab PDF Generation
Tests the actual API endpoint for PDF generation
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port
API_BASE = f"{BASE_URL}/api"

def get_auth_token():
    """Get authentication token for API requests"""
    print("Getting authentication token...")
    
    # Try to get token using test credentials
    login_data = {
        "email": "admin@school.com",  # Adjust based on your test user
        "password": "admin123"        # Adjust based on your test password
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login/", json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token') or data.get('access')
            if token:
                print("✓ Authentication successful")
                return token
            else:
                print("✗ No token in response")
                return None
        else:
            print(f"✗ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Login error: {e}")
        return None

def test_pdf_generation_endpoint(token):
    """Test the PDF generation endpoint"""
    print("Testing PDF generation endpoint...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test data - adjust based on your database
    test_data = {
        "student_id": 1,  # Adjust based on existing student
        "term_id": 1      # Adjust based on existing term
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/reports/report-cards/generate_pdf_report/",
            json=test_data,
            headers=headers
        )
        
        if response.status_code == 200:
            # Check if response is PDF
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' in content_type:
                print("✓ PDF generated successfully")
                
                # Save PDF file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_filename = f"test_report_{timestamp}.pdf"
                pdf_path = os.path.join(os.path.dirname(__file__), pdf_filename)
                
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✓ PDF saved to: {pdf_path}")
                print(f"✓ PDF size: {len(response.content)} bytes")
                
                return True
            else:
                print(f"✗ Unexpected content type: {content_type}")
                print(f"Response: {response.text[:500]}")
                return False
        else:
            print(f"✗ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ API test error: {e}")
        return False

def test_template_preview(token):
    """Test the template preview endpoint"""
    print("Testing template preview endpoint...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/reports/report-cards/template_preview/?token={token}",
            headers=headers
        )
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                print("✓ Template preview generated successfully")
                
                # Save HTML preview
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_filename = f"template_preview_{timestamp}.html"
                html_path = os.path.join(os.path.dirname(__file__), html_filename)
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                print(f"✓ HTML preview saved to: {html_path}")
                return True
            else:
                print(f"✗ Unexpected content type: {content_type}")
                return False
        else:
            print(f"✗ Template preview failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"✗ Template preview error: {e}")
        return False

def check_server_status():
    """Check if the Django server is running"""
    print("Checking server status...")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code in [200, 404]:  # 404 is OK, means server is running
            print("✓ Django server is running")
            return True
        else:
            print(f"✗ Server returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Django server")
        print(f"Make sure the server is running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"✗ Server check error: {e}")
        return False

def run_api_tests():
    """Run all API tests"""
    print("=" * 60)
    print("ReportLab PDF API Test Suite")
    print("=" * 60)
    
    # Check server status
    if not check_server_status():
        print("\n❌ Server is not running. Please start the Django server first:")
        print("   cd backend")
        print("   python manage.py runserver")
        return False
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("\n❌ Authentication failed. Please check:")
        print("   1. Django server is running")
        print("   2. Test user credentials are correct")
        print("   3. Database is accessible")
        return False
    
    # Run tests
    tests = [
        ("Template Preview", lambda: test_template_preview(token)),
        ("PDF Generation", lambda: test_pdf_generation_endpoint(token)),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("API TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} API tests passed")
    
    if passed == total:
        print("🎉 All API tests passed! PDF generation is working via API.")
    else:
        print("❌ Some API tests failed. Check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    print("ReportLab PDF API Test")
    print("Make sure your Django server is running before running this test!")
    print()
    
    success = run_api_tests()
    
    if success:
        print("\n🚀 PDF API is working correctly!")
        print("\nYou can now:")
        print("1. Use the PDF generation in your frontend")
        print("2. Test with real student data")
        print("3. Customize the PDF template as needed")
    else:
        print("\n🔧 Please fix the API issues before using PDF generation.")
    
    input("\nPress Enter to exit...")