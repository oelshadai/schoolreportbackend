#!/usr/bin/env python3
"""
Simple health check for API connectivity
"""
import requests
import json

def test_api_health():
    """Test basic API connectivity"""
    base_url = "https://school-report-saas.onrender.com"
    
    print(f"Testing API connectivity to: {base_url}")
    
    try:
        # Test basic health endpoint
        response = requests.get(f"{base_url}/api/", timeout=10)
        print(f"API Root Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API is accessible")
        else:
            print(f"❌ API returned status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API connection failed: {e}")
    
    try:
        # Test CORS preflight
        headers = {
            'Origin': 'https://school-report-saas-1.onrender.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,authorization'
        }
        response = requests.options(f"{base_url}/api/auth/login/", headers=headers, timeout=10)
        print(f"CORS Preflight Status: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print("✅ CORS is properly configured")
        else:
            print(f"❌ CORS issue detected: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ CORS test failed: {e}")

if __name__ == "__main__":
    test_api_health()