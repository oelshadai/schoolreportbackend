#!/usr/bin/env python3
"""
Django Server Diagnostic Script
Tests different ports and configurations
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_port(port):
    """Test if a port is accessible"""
    try:
        response = requests.get(f'http://127.0.0.1:{port}/api/auth/csrf-token/', timeout=5)
        return True, response.status_code
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def check_django_setup():
    """Check if Django is properly configured"""
    try:
        # Test Django settings
        result = subprocess.run([
            sys.executable, '-c', 
            'import django; django.setup(); print("Django setup OK")'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ Django setup is working")
            return True
        else:
            print(f"❌ Django setup failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Django setup error: {e}")
        return False

def start_server_on_port(port):
    """Try to start Django server on specific port"""
    print(f"🚀 Trying to start server on port {port}...")
    
    try:
        # Start server in background
        process = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}'
        ], cwd=Path(__file__).parent)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Test if it's working
        working, status = test_port(port)
        
        if working:
            print(f"✅ Server started successfully on port {port}")
            print(f"   Status: {status}")
            print(f"   URL: http://127.0.0.1:{port}/api/auth/csrf-token/")
            return process, port
        else:
            print(f"❌ Server not responding on port {port}: {status}")
            process.terminate()
            return None, None
            
    except Exception as e:
        print(f"❌ Failed to start server on port {port}: {e}")
        return None, None

def main():
    print("🔍 Django Server Diagnostic")
    print("=" * 40)
    
    # Check Django setup
    if not check_django_setup():
        print("\n❌ Fix Django setup first!")
        return False
    
    # Test common ports
    ports_to_try = [8000, 8001, 8080, 3000]
    
    print("\n🧪 Testing existing servers...")
    for port in ports_to_try:
        working, status = test_port(port)
        if working:
            print(f"✅ Found working server on port {port} (Status: {status})")
            print(f"   Use this URL: http://127.0.0.1:{port}/api/auth/csrf-token/")
            
            # Update frontend config
            print(f"\n🔧 Update your frontend .env file:")
            print(f"   VITE_API_URL=http://127.0.0.1:{port}/api")
            return True
        else:
            print(f"❌ Port {port}: {status}")
    
    print("\n🚀 No working servers found. Trying to start one...")
    
    # Try to start server on available port
    for port in ports_to_try:
        process, working_port = start_server_on_port(port)
        if process and working_port:
            print(f"\n🎉 SUCCESS! Server running on port {working_port}")
            print(f"   Frontend should use: http://127.0.0.1:{working_port}/api")
            print(f"   Test URL: http://127.0.0.1:{working_port}/api/auth/csrf-token/")
            
            # Keep server running
            try:
                print("\n⏳ Server is running. Press Ctrl+C to stop...")
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Stopping server...")
                process.terminate()
            
            return True
    
    print("\n❌ Could not start Django server on any port!")
    print("   Check for errors in Django configuration")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)