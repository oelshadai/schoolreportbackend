#!/usr/bin/env python3
"""
Test Django server on multiple ports
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_server_on_port(port):
    """Test if Django server works on a specific port"""
    print(f"🚀 Testing Django server on port {port}...")
    
    try:
        # Start Django server
        process = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}'
        ], cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(5)
        
        # Test if server responds
        try:
            response = requests.get(f'http://127.0.0.1:{port}/admin/', timeout=5)
            if response.status_code in [200, 302]:  # 302 is redirect to login
                print(f"✅ Server working on port {port}!")
                print(f"   Admin URL: http://127.0.0.1:{port}/admin/")
                print(f"   API URL: http://127.0.0.1:{port}/api/auth/csrf-token/")
                
                # Test API endpoint
                try:
                    api_response = requests.get(f'http://127.0.0.1:{port}/api/auth/csrf-token/', timeout=5)
                    if api_response.status_code == 200:
                        print(f"✅ API endpoint working!")
                        print(f"   Update your frontend .env file:")
                        print(f"   VITE_API_URL=http://127.0.0.1:{port}/api")
                        
                        # Keep server running
                        print(f"\n⏳ Server is running on port {port}. Press Ctrl+C to stop...")
                        try:
                            process.wait()
                        except KeyboardInterrupt:
                            print("\n🛑 Stopping server...")
                            process.terminate()
                        
                        return True
                    else:
                        print(f"❌ API endpoint not working: {api_response.status_code}")
                except Exception as e:
                    print(f"❌ API test failed: {e}")
                
            else:
                print(f"❌ Server responded with status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to server on port {port}")
        except requests.exceptions.Timeout:
            print(f"❌ Server timeout on port {port}")
        except Exception as e:
            print(f"❌ Error testing port {port}: {e}")
        
        # Stop the server
        process.terminate()
        return False
        
    except Exception as e:
        print(f"❌ Failed to start server on port {port}: {e}")
        return False

def main():
    print("🔍 DJANGO SERVER PORT TEST")
    print("=" * 30)
    
    # Test different ports
    ports = [8000, 8001, 8080, 3000, 5000]
    
    for port in ports:
        if test_server_on_port(port):
            return True
        print()  # Empty line between tests
    
    print("❌ Could not start Django server on any port!")
    print("\nPossible issues:")
    print("1. Django is not properly installed")
    print("2. Database issues")
    print("3. Settings configuration problems")
    print("4. Port conflicts")
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)