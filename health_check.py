#!/usr/bin/env python3
"""
Quick health check for the Django backend
"""

import requests
import time
import sys

def test_backend_health():
    """Test if backend is responding"""
    base_url = "http://127.0.0.1:8000"
    
    print("🔍 Testing backend health...")
    
    # Test basic connectivity
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/api/", timeout=10)
        response_time = time.time() - start_time
        
        print(f"✅ Backend responding in {response_time:.2f}s (Status: {response.status_code})")
        
        if response_time > 5:
            print("⚠️ Slow response time - this might cause login timeouts")
            
    except requests.exceptions.Timeout:
        print("❌ Backend timeout - server is too slow")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend not running - start with 'python manage.py runserver'")
        return False
    except Exception as e:
        print(f"❌ Backend error: {e}")
        return False
    
    # Test auth endpoints
    auth_endpoints = [
        "/api/auth/student-login/",
        "/api/auth/teacher-login/", 
        "/api/auth/admin-login/"
    ]
    
    for endpoint in auth_endpoints:
        try:
            start_time = time.time()
            response = requests.post(f"{base_url}{endpoint}", 
                                   json={"test": "data"}, 
                                   timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code in [400, 401]:  # Expected for invalid data
                print(f"✅ {endpoint} - Working ({response_time:.2f}s)")
            elif response.status_code == 404:
                print(f"❌ {endpoint} - Not found")
            else:
                print(f"⚠️ {endpoint} - Unexpected status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint} - Timeout")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
    
    return True

if __name__ == "__main__":
    success = test_backend_health()
    if success:
        print("\n🎉 Backend health check completed!")
        print("\nIf you're still having login timeouts:")
        print("1. Restart the Django server")
        print("2. Clear browser cache")
        print("3. Check network connection")
    else:
        print("\n❌ Backend health check failed!")
        sys.exit(1)