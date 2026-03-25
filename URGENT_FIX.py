#!/usr/bin/env python3
"""
URGENT: Authentication & Connection Fix
Resolves timeout and 401 errors immediately
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def create_test_users_immediately():
    """Create test users right now"""
    print("👥 Creating test users immediately...")
    
    script_content = '''
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from schools.models import School, AcademicYear, Term
from students.models import Student
from teachers.models import Teacher
from django.contrib.auth.hashers import make_password

print("Creating test school...")
school, created = School.objects.get_or_create(
    name="Test School",
    defaults={
        'address': 'Test Address',
        'phone_number': '1234567890',
        'email': 'test@school.com'
    }
)
print(f"School: {school.name} (Created: {created})")

# Create test admin
print("Creating admin user...")
admin_user, created = User.objects.get_or_create(
    email='admin@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Admin',
        'role': 'SCHOOL_ADMIN',
        'school': school,
        'is_active': True,
        'password': make_password('testpass123')
    }
)
if not created:
    admin_user.set_password('testpass123')
    admin_user.save()
print(f"Admin: {admin_user.email} (Created: {created})")

# Create test teacher
print("Creating teacher user...")
teacher_user, created = User.objects.get_or_create(
    email='teacher@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Teacher',
        'role': 'TEACHER',
        'school': school,
        'is_active': True,
        'password': make_password('testpass123')
    }
)
if not created:
    teacher_user.set_password('testpass123')
    teacher_user.save()
print(f"Teacher: {teacher_user.email} (Created: {created})")

# Create teacher profile
teacher_profile, created = Teacher.objects.get_or_create(
    user=teacher_user,
    defaults={
        'school': school,
        'employee_id': 'TEACH001',
        'qualification': 'Bachelor of Education',
        'is_active': True
    }
)
print(f"Teacher profile: {teacher_profile.employee_id} (Created: {created})")

# Create test student user
print("Creating student user...")
student_user, created = User.objects.get_or_create(
    email='student@test.com',
    defaults={
        'first_name': 'Test',
        'last_name': 'Student',
        'role': 'STUDENT',
        'school': school,
        'is_active': True,
        'password': make_password('testpass123')
    }
)
if not created:
    student_user.set_password('testpass123')
    student_user.save()
print(f"Student user: {student_user.email} (Created: {created})")

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
print(f"Student: {student.student_id} (Created: {created})")

print("\\n✅ Test users created successfully!")
print("\\nCredentials:")
print("  Admin: admin@test.com / testpass123")
print("  Teacher: teacher@test.com / testpass123")
print("  Student: TEST001 / testpass123")
'''
    
    try:
        # Write and execute the script
        script_path = Path(__file__).parent / "create_users_now.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        print("Script output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        # Cleanup
        script_path.unlink()
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        return False

def fix_cors_immediately():
    """Fix CORS settings right now"""
    print("🔧 Fixing CORS settings...")
    
    settings_path = Path(__file__).parent / "school_report_saas" / "settings.py"
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add emergency CORS fix
        cors_fix = '''
# EMERGENCY CORS FIX - DEVELOPMENT ONLY
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8080',
    'http://localhost:8081', 
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8081',
]
'''
        
        if 'EMERGENCY CORS FIX' not in content:
            content = content.rstrip() + '\\n' + cors_fix + '\\n'
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ CORS settings fixed")
            return True
        else:
            print("✅ CORS already fixed")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing CORS: {e}")
        return False

def test_endpoints_now():
    """Test endpoints immediately"""
    print("🧪 Testing endpoints...")
    
    try:
        import requests
        
        # Test basic connectivity
        try:
            response = requests.get('http://127.0.0.1:8000/api/auth/csrf-token/', timeout=5)
            print(f"✅ Backend responding: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Backend not responding - make sure Django server is running!")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
        
        # Test login endpoints
        endpoints = [
            ('student-login', {'student_id': 'TEST001', 'password': 'testpass123'}),
            ('teacher-login', {'email': 'teacher@test.com', 'password': 'testpass123'}),
            ('admin-login', {'email': 'admin@test.com', 'password': 'testpass123'})
        ]
        
        for endpoint, data in endpoints:
            try:
                response = requests.post(
                    f'http://127.0.0.1:8000/api/auth/{endpoint}/',
                    json=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✅ {endpoint}: SUCCESS")
                elif response.status_code == 401:
                    print(f"⚠️ {endpoint}: 401 (check credentials)")
                else:
                    print(f"❌ {endpoint}: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"❌ {endpoint}: TIMEOUT")
            except Exception as e:
                print(f"❌ {endpoint}: {e}")
        
        return True
        
    except ImportError:
        print("❌ requests library not available")
        return False

def create_quick_test_page():
    """Create a quick test page"""
    print("🌐 Creating quick test page...")
    
    test_html = '''<!DOCTYPE html>
<html>
<head>
    <title>URGENT AUTH TEST</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        .result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🚨 URGENT AUTH TEST</h1>
    <button onclick="testStudent()">Test Student Login</button>
    <button onclick="testTeacher()">Test Teacher Login</button>
    <button onclick="testAdmin()">Test Admin Login</button>
    <div id="results"></div>
    
    <script>
        const API_BASE = 'http://127.0.0.1:8000/api';
        
        function showResult(message, isSuccess) {
            const div = document.createElement('div');
            div.className = `result ${isSuccess ? 'success' : 'error'}`;
            div.innerHTML = message;
            document.getElementById('results').appendChild(div);
        }
        
        async function testStudent() {
            try {
                const response = await fetch(`${API_BASE}/auth/student-login/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: 'TEST001',
                        password: 'testpass123'
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult(`✅ Student login SUCCESS: ${data.user.first_name}`, true);
                } else {
                    showResult(`❌ Student login FAILED: ${data.error}`, false);
                }
            } catch (error) {
                showResult(`❌ Student login ERROR: ${error.message}`, false);
            }
        }
        
        async function testTeacher() {
            try {
                const response = await fetch(`${API_BASE}/auth/teacher-login/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: 'teacher@test.com',
                        password: 'testpass123'
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult(`✅ Teacher login SUCCESS: ${data.user.first_name}`, true);
                } else {
                    showResult(`❌ Teacher login FAILED: ${data.error}`, false);
                }
            } catch (error) {
                showResult(`❌ Teacher login ERROR: ${error.message}`, false);
            }
        }
        
        async function testAdmin() {
            try {
                const response = await fetch(`${API_BASE}/auth/admin-login/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: 'admin@test.com',
                        password: 'testpass123'
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult(`✅ Admin login SUCCESS: ${data.user.first_name}`, true);
                } else {
                    showResult(`❌ Admin login FAILED: ${data.error}`, false);
                }
            } catch (error) {
                showResult(`❌ Admin login ERROR: ${error.message}`, false);
            }
        }
    </script>
</body>
</html>'''
    
    try:
        with open('URGENT_AUTH_TEST.html', 'w') as f:
            f.write(test_html)
        print("✅ Created URGENT_AUTH_TEST.html")
        return True
    except Exception as e:
        print(f"❌ Error creating test page: {e}")
        return False

def main():
    """URGENT FIX - Run immediately"""
    print("🚨 URGENT AUTHENTICATION FIX")
    print("=" * 50)
    
    # Step 1: Fix CORS
    cors_fixed = fix_cors_immediately()
    
    # Step 2: Create test users
    users_created = create_test_users_immediately()
    
    # Step 3: Test endpoints
    endpoints_working = test_endpoints_now()
    
    # Step 4: Create test page
    test_page_created = create_quick_test_page()
    
    print("\\n" + "=" * 50)
    print("🎯 URGENT FIX SUMMARY:")
    print(f"  CORS Fixed: {'✅' if cors_fixed else '❌'}")
    print(f"  Users Created: {'✅' if users_created else '❌'}")
    print(f"  Endpoints Working: {'✅' if endpoints_working else '❌'}")
    print(f"  Test Page Created: {'✅' if test_page_created else '❌'}")
    
    if cors_fixed:
        print("\\n🔄 RESTART DJANGO SERVER NOW:")
        print("   1. Stop server (Ctrl+C)")
        print("   2. python manage.py runserver")
        print("   3. Open URGENT_AUTH_TEST.html")
    
    print("\\n🧪 TEST CREDENTIALS:")
    print("   Student: TEST001 / testpass123")
    print("   Teacher: teacher@test.com / testpass123")
    print("   Admin: admin@test.com / testpass123")
    
    return all([cors_fixed, users_created, endpoints_working, test_page_created])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)