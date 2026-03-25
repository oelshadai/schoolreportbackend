#!/usr/bin/env python3
"""
Test assignment endpoints after URL reordering
"""

import requests
import json

def test_assignment_endpoints():
    """Test assignment endpoints with authentication"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing assignment endpoints...")
    
    # First, try to login as a teacher to get auth token
    login_data = {
        "email": "teacher@test.com",
        "password": "testpass123"
    }
    
    try:
        login_response = requests.post(f"{base_url}/api/auth/teacher-login/", json=login_data, timeout=10)
        if login_response.status_code == 200:
            token = login_response.json().get('access')
            headers = {'Authorization': f'Bearer {token}'}
            print("✓ Teacher login successful")
            
            # Test assignment endpoints with auth
            test_urls = [
                f"{base_url}/api/assignments/teacher/",
                f"{base_url}/api/assignments/teacher/1/publish_assignment/",
                f"{base_url}/api/assignments/teacher/1/submissions/",
            ]
            
            for url in test_urls:
                try:
                    if "publish_assignment" in url:
                        response = requests.post(url, json={}, headers=headers, timeout=5)
                    else:
                        response = requests.get(url, headers=headers, timeout=5)
                    
                    if response.status_code == 404:
                        print(f"✗ {url} - Still 404")
                    elif response.status_code in [200, 201, 400, 401]:
                        print(f"✓ {url} - Working (status: {response.status_code})")
                    else:
                        print(f"? {url} - Status: {response.status_code}")
                        
                except Exception as e:
                    print(f"✗ {url} - Error: {e}")
        else:
            print(f"✗ Teacher login failed: {login_response.status_code}")
            print("Using test without auth...")
            
            # Test without auth (should get 401, not 404)
            test_urls = [
                f"{base_url}/api/assignments/teacher/1/publish_assignment/",
                f"{base_url}/api/assignments/teacher/1/submissions/",
            ]
            
            for url in test_urls:
                try:
                    response = requests.post(url, json={}, timeout=5)
                    if response.status_code == 404:
                        print(f"✗ {url} - Still 404 (routing issue)")
                    elif response.status_code == 401:
                        print(f"✓ {url} - Working (needs auth)")
                    else:
                        print(f"? {url} - Status: {response.status_code}")
                except Exception as e:
                    print(f"✗ {url} - Error: {e}")
                    
    except Exception as e:
        print(f"✗ Login test failed: {e}")

if __name__ == "__main__":
    test_assignment_endpoints()