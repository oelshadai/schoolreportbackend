#!/usr/bin/env python3
"""
Test assignment URLs to verify publish_assignment endpoint
"""

import requests
import json

def test_assignment_urls():
    """Test assignment endpoints"""
    base_url = "http://127.0.0.1:8000/api/assignments"
    
    print("Testing assignment URLs...")
    
    # Test endpoints that should exist
    test_urls = [
        f"{base_url}/teacher/",
        f"{base_url}/teacher/1/",
        f"{base_url}/teacher/1/publish_assignment/",
        f"{base_url}/teacher/1/submissions/",
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 401:
                print(f"OK {url} - Exists (needs auth)")
            elif response.status_code == 404:
                print(f"ERROR {url} - Not found")
            elif response.status_code == 405:
                print(f"OK {url} - Exists (wrong method)")
            else:
                print(f"WARN {url} - Status: {response.status_code}")
        except Exception as e:
            print(f"ERROR {url} - Error: {e}")
    
    # Test POST to publish_assignment
    print("\nTesting POST to publish_assignment...")
    try:
        response = requests.post(
            f"{base_url}/teacher/1/publish_assignment/",
            json={"test": "data"},
            timeout=5
        )
        if response.status_code == 401:
            print("OK publish_assignment endpoint exists (needs auth)")
        elif response.status_code == 404:
            print("ERROR publish_assignment endpoint not found")
        else:
            print(f"WARN publish_assignment - Status: {response.status_code}")
    except Exception as e:
        print(f"ERROR publish_assignment - Error: {e}")

if __name__ == "__main__":
    test_assignment_urls()