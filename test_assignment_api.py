#!/usr/bin/env python3
"""
Test script to verify assignment API endpoints
"""
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

def test_assignment_endpoints():
    """Test assignment API endpoints"""
    print("Testing Assignment API Endpoints...")
    
    # Test data
    test_credentials = {
        "email": "teacher@example.com",  # Replace with actual teacher email
        "password": "password123"        # Replace with actual password
    }
    
    session = requests.Session()
    
    try:
        # 1. Login to get authentication token
        print("1. Testing login...")
        login_response = session.post(f"{API_BASE}/auth/login/", json=test_credentials)
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        login_data = login_response.json()
        access_token = login_data.get('access')
        
        if not access_token:
            print("❌ No access token received")
            return False
        
        print("✅ Login successful")
        
        # Set authorization header
        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })
        
        # 2. Test list assignments
        print("\\n2. Testing list assignments...")
        list_response = session.get(f"{API_BASE}/assignments/teacher/")
        
        print(f"Status: {list_response.status_code}")
        if list_response.status_code == 200:
            assignments = list_response.json()
            print(f"✅ Found {assignments.get('count', 0)} assignments")
            
            # If we have assignments, test individual operations
            if assignments.get('results') and len(assignments['results']) > 0:
                assignment_id = assignments['results'][0]['id']
                print(f"Testing with assignment ID: {assignment_id}")
                
                # 3. Test retrieve assignment
                print("\\n3. Testing retrieve assignment...")
                retrieve_response = session.get(f"{API_BASE}/assignments/teacher/{assignment_id}/")
                print(f"Status: {retrieve_response.status_code}")
                
                if retrieve_response.status_code == 200:
                    print("✅ Retrieve assignment successful")
                    assignment_data = retrieve_response.json()
                    print(f"Assignment: {assignment_data.get('title', 'Unknown')}")
                else:
                    print(f"❌ Retrieve failed: {retrieve_response.text}")
                
                # 4. Test publish assignment
                print("\\n4. Testing publish assignment...")
                publish_response = session.post(f"{API_BASE}/assignments/teacher/{assignment_id}/publish/")
                print(f"Status: {publish_response.status_code}")
                
                if publish_response.status_code == 200:
                    print("✅ Publish assignment successful")
                else:
                    print(f"❌ Publish failed: {publish_response.text}")
                
                # 5. Test update assignment
                print("\\n5. Testing update assignment...")
                update_data = {
                    "title": "Updated Test Assignment",
                    "description": "Updated description"
                }
                update_response = session.put(f"{API_BASE}/assignments/teacher/{assignment_id}/", json=update_data)
                print(f"Status: {update_response.status_code}")
                
                if update_response.status_code == 200:
                    print("✅ Update assignment successful")
                else:
                    print(f"❌ Update failed: {update_response.text}")
                
                # 6. Test get submissions
                print("\\n6. Testing get submissions...")
                submissions_response = session.get(f"{API_BASE}/assignments/teacher/{assignment_id}/submissions/")
                print(f"Status: {submissions_response.status_code}")
                
                if submissions_response.status_code == 200:
                    print("✅ Get submissions successful")
                    submissions_data = submissions_response.json()
                    print(f"Found {len(submissions_data.get('submissions', []))} submissions")
                else:
                    print(f"❌ Get submissions failed: {submissions_response.text}")
                
            else:
                print("ℹ️  No assignments found to test individual operations")
        else:
            print(f"❌ List assignments failed: {list_response.text}")
        
        # 7. Test create assignment
        print("\\n7. Testing create assignment...")
        create_data = {
            "title": "Test Assignment API",
            "description": "Testing assignment creation via API",
            "assignment_type": "HOMEWORK",
            "class_instance": 1,  # Replace with actual class ID
            "due_date": "2024-12-31T23:59:59Z",
            "max_score": 10
        }
        
        create_response = session.post(f"{API_BASE}/assignments/teacher/", json=create_data)
        print(f"Status: {create_response.status_code}")
        
        if create_response.status_code == 201:
            print("✅ Create assignment successful")
            created_assignment = create_response.json()
            print(f"Created assignment ID: {created_assignment.get('id')}")
            
            # Clean up - delete the test assignment
            if created_assignment.get('id'):
                delete_response = session.delete(f"{API_BASE}/assignments/teacher/{created_assignment['id']}/")
                if delete_response.status_code == 200:
                    print("✅ Test assignment cleaned up")
        else:
            print(f"❌ Create assignment failed: {create_response.text}")
        
        print("\\n" + "="*50)
        print("✅ Assignment API endpoint tests completed!")
        print("="*50)
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure Django server is running on http://127.0.0.1:8000")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    print("Assignment API Endpoint Tester")
    print("="*50)
    print("Make sure:")
    print("1. Django server is running (python manage.py runserver)")
    print("2. You have a teacher account created")
    print("3. Update test_credentials in this script")
    print("="*50)
    
    success = test_assignment_endpoints()
    if success:
        print("\\n🎉 All tests completed! Check the output above for any issues.")
    else:
        print("\\n❌ Tests failed. Check the error messages above.")