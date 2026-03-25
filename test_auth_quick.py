#!/usr/bin/env python
"""
Quick authentication test for teacher login
"""

import requests
import json

def test_teacher_login():
    """Test teacher login endpoint"""
    
    # Backend URL
    base_url = "http://127.0.0.1:8000"
    
    # Test credentials (using the teacher we found earlier)
    login_data = {
        "email": "nanaamaadomah18@gmail.com",
        "password": "password123"  # You may need to update this
    }
    
    print("Testing teacher login...")
    print(f"Email: {login_data['email']}")
    
    try:
        # Test login
        response = requests.post(
            f"{base_url}/api/auth/teacher-login/",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Login Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {data.get('access', 'N/A')[:50]}...")
            print(f"User Role: {data.get('user', {}).get('role', 'N/A')}")
            print(f"School ID: {data.get('user', {}).get('school_id', 'N/A')}")
            
            # Test dashboard with token
            access_token = data.get('access')
            if access_token:
                print("\nTesting dashboard access...")
                dashboard_response = requests.get(
                    f"{base_url}/api/auth/teacher-dashboard/",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"Dashboard Response Status: {dashboard_response.status_code}")
                
                if dashboard_response.status_code == 200:
                    dashboard_data = dashboard_response.json()
                    print("✅ Dashboard access successful!")
                    print(f"Teacher Name: {dashboard_data.get('teacher', {}).get('name', 'N/A')}")
                    print(f"School: {dashboard_data.get('teacher', {}).get('school', 'N/A')}")
                    print(f"Classes: {len(dashboard_data.get('assigned_classes', []))}")
                    print(f"Subjects: {len(dashboard_data.get('teaching_subjects', []))}")
                else:
                    print(f"❌ Dashboard access failed: {dashboard_response.text}")
            
        else:
            print(f"❌ Login failed: {response.text}")
            
            # Try with different password
            print("\nTrying with default password...")
            login_data["password"] = "defaultpassword"
            
            response2 = requests.post(
                f"{base_url}/api/auth/teacher-login/",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Second attempt status: {response2.status_code}")
            if response2.status_code == 200:
                print("✅ Login successful with default password!")
            else:
                print(f"❌ Still failed: {response2.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the Django server running?")
        print("Start server with: python manage.py runserver 127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_teacher_login()