"""
Test script for SystemSettings API endpoints
Run this to verify the settings page will work correctly
"""

import requests
import json

# Configuration
API_URL = "http://localhost:8000"
# You'll need to replace this with a valid token from your system
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_get_settings():
    """Test fetching school settings"""
    print("\n=== Testing GET /api/schools/settings/ ===")
    try:
        response = requests.get(f"{API_URL}/api/schools/settings/", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully fetched settings")
            print(f"School Name: {data.get('name')}")
            print(f"Current Term: {data.get('current_term')}")
            print(f"Score Entry Mode: {data.get('score_entry_mode')}")
            print(f"Report Template: {data.get('report_template')}")
            print(f"Show Class Average: {data.get('show_class_average')}")
            print(f"Grade Scale A Min: {data.get('grade_scale_a_min')}")
            return data
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_get_terms():
    """Test fetching terms"""
    print("\n=== Testing GET /api/schools/terms/ ===")
    try:
        response = requests.get(f"{API_URL}/api/schools/terms/", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully fetched {len(data)} terms")
            for term in data:
                print(f"  - {term.get('display_name')} (ID: {term.get('id')})")
            return data
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_update_settings(current_settings):
    """Test updating school settings"""
    print("\n=== Testing PATCH /api/schools/settings/ ===")
    
    # Test data - update a few fields
    update_data = {
        "show_class_average": not current_settings.get('show_class_average', True),
        "show_position_in_class": not current_settings.get('show_position_in_class', True),
        "grade_scale_a_min": 85  # Change grade A minimum
    }
    
    print(f"Updating settings: {json.dumps(update_data, indent=2)}")
    
    try:
        response = requests.patch(
            f"{API_URL}/api/schools/settings/", 
            headers=headers,
            json=update_data
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully updated settings")
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("=" * 60)
    print("SystemSettings API Test Suite")
    print("=" * 60)
    
    # Test 1: Get current settings
    settings = test_get_settings()
    if not settings:
        print("\n❌ Failed to fetch settings. Check:")
        print("  1. Backend server is running (python manage.py runserver)")
        print("  2. TOKEN is valid (get from login)")
        print("  3. User has a school associated")
        return
    
    # Test 2: Get terms
    terms = test_get_terms()
    if not terms:
        print("\n⚠️  No terms found. You may need to create terms first.")
    
    # Test 3: Update settings
    print("\n" + "=" * 60)
    response = input("Do you want to test updating settings? (y/n): ")
    if response.lower() == 'y':
        test_update_settings(settings)
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print("✅ GET /api/schools/settings/ - Working" if settings else "❌ GET /api/schools/settings/ - Failed")
    print("✅ GET /api/schools/terms/ - Working" if terms else "⚠️  GET /api/schools/terms/ - No data")
    print("\nTo use the SystemSettings page:")
    print("1. Make sure backend is running")
    print("2. Login to get a valid token")
    print("3. Navigate to the SystemSettings page")
    print("4. All settings should load and save correctly")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Update the TOKEN variable with a valid token from your system")
    print("You can get a token by:")
    print("1. Login via the API or frontend")
    print("2. Check localStorage in browser dev tools")
    print("3. Or use the token from a successful login response\n")
    
    proceed = input("Have you updated the TOKEN? (y/n): ")
    if proceed.lower() == 'y':
        main()
    else:
        print("\nPlease update the TOKEN variable in this script and run again.")
