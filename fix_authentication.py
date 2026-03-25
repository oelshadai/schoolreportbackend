#!/usr/bin/env python3
"""
Authentication Fix Script
Resolves 401 Unauthorized errors and ensures proper API connectivity
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_django_server():
    """Check if Django server is running"""
    print("🔍 Checking Django server status...")
    
    try:
        import requests
        response = requests.get('http://127.0.0.1:8000/api/auth/csrf-token/', timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running and responding")
            return True
        else:
            print(f"⚠️ Django server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Django server is not running")
        return False
    except Exception as e:
        print(f"❌ Error checking Django server: {e}")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    print("🧪 Testing authentication endpoints...")
    
    endpoints = [
        '/api/auth/student-login/',
        '/api/auth/teacher-login/',
        '/api/auth/admin-login/',
        '/api/auth/superadmin-login/'
    ]
    
    try:
        import requests
        
        for endpoint in endpoints:
            url = f'http://127.0.0.1:8000{endpoint}'
            
            # Test with invalid credentials (should return 401 or 400, not 404)
            response = requests.post(url, json={
                'email': 'test@example.com',
                'password': 'test'
            }, timeout=5)
            
            if response.status_code in [400, 401]:
                print(f"✅ {endpoint} - Working (status: {response.status_code})")
            elif response.status_code == 404:
                print(f"❌ {endpoint} - Not found (404)")
            else:
                print(f"⚠️ {endpoint} - Unexpected status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")

def fix_cors_settings():
    """Fix CORS settings in Django"""
    print("🔧 Checking CORS settings...")
    
    settings_path = Path(__file__).parent / "school_report_saas" / "settings.py"
    
    if not settings_path.exists():
        print(f"❌ Settings file not found: {settings_path}")
        return False
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if CORS is properly configured
        cors_fixes = []
        
        if 'CORS_ALLOW_ALL_ORIGINS = True' not in content:
            cors_fixes.append("# Temporary CORS fix for development\nCORS_ALLOW_ALL_ORIGINS = True")
        
        if 'CORS_ALLOW_CREDENTIALS = True' not in content:
            cors_fixes.append("CORS_ALLOW_CREDENTIALS = True")
        
        if cors_fixes:
            # Add CORS fixes
            cors_config = '\n\n' + '\n'.join(cors_fixes) + '\n'
            content = content.rstrip() + cors_config
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Added CORS fixes to settings.py")
            print("⚠️ Remember to restart Django server")
            return True
        else:
            print("✅ CORS settings look good")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing CORS settings: {e}")
        return False

def create_test_users():
    """Create test users for authentication testing"""
    print("👥 Creating test users...")
    
    manage_py = Path(__file__).parent / "manage.py"
    if not manage_py.exists():
        print("❌ manage.py not found")
        return False
    
    # Create test script
    test_script = '''
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from schools.models import School, AcademicYear, Term
from students.models import Student
from teachers.models import Teacher

# Create test school
school, created = School.objects.get_or_create(
    name="Test School",
    defaults={
        'address': 'Test Address',
        'phone_number': '1234567890',
        'email': 'test@school.com'
    }
)

# Create test admin
admin_user, created = User.objects.get_or_create(
    email='admin@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Admin',
        'role': 'ADMIN',
        'school': school,
        'is_active': True
    }
)
if created:
    admin_user.set_password('testpass123')
    admin_user.save()
    print(f"Created admin: admin@test.com / testpass123")

# Create test teacher
teacher_user, created = User.objects.get_or_create(
    email='teacher@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Teacher',
        'role': 'TEACHER',
        'school': school,
        'is_active': True
    }
)
if created:
    teacher_user.set_password('testpass123')
    teacher_user.save()
    print(f"Created teacher: teacher@test.com / testpass123")

# Create test student
student_user, created = User.objects.get_or_create(
    email='student@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Student',
        'role': 'STUDENT',
        'school': school,
        'is_active': True
    }
)
if created:
    student_user.set_password('testpass123')
    student_user.save()

# Create student profile
student, created = Student.objects.get_or_create(
    student_id='TEST001',
    defaults={
        'user': student_user,
        'school': school,
        'first_name': 'Test',
        'last_name': 'Student',
        'date_of_birth': '2005-01-01',
        'is_active': True
    }
)
if created:
    print(f"Created student: TEST001 / testpass123")

print("Test users created successfully!")
'''
    
    try:
        # Write test script to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        # Run the script
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ Test users created successfully")
            print(result.stdout)
        else:
            print(f"❌ Error creating test users: {result.stderr}")
        
        # Cleanup
        os.unlink(script_path)
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")

def restart_django_server():
    """Instructions to restart Django server"""
    print("\n🔄 IMPORTANT: Restart your Django server to apply changes")
    print("1. Stop the current server (Ctrl+C)")
    print("2. Run: python manage.py runserver")
    print("3. Test the frontend again")

def create_frontend_test():
    """Create a simple frontend test"""
    print("🌐 Creating frontend test...")
    
    test_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Auth Test</title>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
</head>
<body>
    <h1>Authentication Test</h1>
    <div id="results"></div>
    
    <script>
        const API_BASE = 'http://127.0.0.1:8000/api';
        
        async function testAuth() {
            const results = document.getElementById('results');
            results.innerHTML = '<p>Testing authentication...</p>';
            
            try {
                // Test student login
                const response = await axios.post(`${API_BASE}/auth/student-login/`, {
                    student_id: 'TEST001',
                    password: 'testpass123'
                });
                
                results.innerHTML += `<p style="color: green;">✅ Student login successful!</p>`;
                results.innerHTML += `<pre>${JSON.stringify(response.data, null, 2)}</pre>`;
                
            } catch (error) {
                if (error.response) {
                    results.innerHTML += `<p style="color: red;">❌ Student login failed: ${error.response.status}</p>`;
                    results.innerHTML += `<pre>${JSON.stringify(error.response.data, null, 2)}</pre>`;
                } else {
                    results.innerHTML += `<p style="color: red;">❌ Network error: ${error.message}</p>`;
                }
            }
        }
        
        // Auto-run test
        testAuth();
    </script>
</body>
</html>
'''
    
    try:
        with open('frontend_auth_test.html', 'w') as f:
            f.write(test_html)
        print("✅ Created frontend_auth_test.html")
        print("   Open this file in your browser to test authentication")
    except Exception as e:
        print(f"❌ Error creating frontend test: {e}")

def main():
    """Main fix process"""
    print("🚀 Authentication Fix Script")
    print("=" * 50)
    
    # Check Django server
    if not check_django_server():
        print("\n❌ Django server is not running!")
        print("Please start the Django server first:")
        print("   cd backend")
        print("   python manage.py runserver")
        return False
    
    # Test endpoints
    test_auth_endpoints()
    
    # Fix CORS settings
    cors_fixed = fix_cors_settings()
    
    # Create test users
    create_test_users()
    
    # Create frontend test
    create_frontend_test()
    
    if cors_fixed:
        restart_django_server()
    
    print("\n🎉 Authentication fix completed!")
    print("\nTest credentials:")
    print("  Admin: admin@test.com / testpass123")
    print("  Teacher: teacher@test.com / testpass123") 
    print("  Student: TEST001 / testpass123")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)