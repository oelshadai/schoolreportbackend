#!/usr/bin/env python3
"""
wkhtmltopdf Installation Script for School Report SaaS
Automatically installs wkhtmltopdf based on the operating system
"""

import os
import sys
import platform
import subprocess
import urllib.request
import tempfile

def install_wkhtmltopdf():
    """Install wkhtmltopdf based on the operating system"""
    system = platform.system().lower()
    
    print(f"Detected OS: {system}")
    print("Installing wkhtmltopdf...")
    
    if system == "windows":
        install_windows()
    elif system == "linux":
        install_linux()
    elif system == "darwin":  # macOS
        install_macos()
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

def install_windows():
    """Install wkhtmltopdf on Windows"""
    print("Installing wkhtmltopdf for Windows...")
    
    # Download URL for Windows installer
    url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
    
    print("Downloading wkhtmltopdf installer...")
    print("Please run the downloaded installer manually.")
    print(f"Download URL: {url}")
    
    # Try to open the URL in browser
    try:
        import webbrowser
        webbrowser.open(url)
    except:
        pass
    
    print("\nAfter installation, wkhtmltopdf should be available at:")
    print("C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")

def install_linux():
    """Install wkhtmltopdf on Linux"""
    print("Installing wkhtmltopdf for Linux...")
    
    # Try different package managers
    try:
        # Ubuntu/Debian
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "wkhtmltopdf"], check=True)
        print("✅ wkhtmltopdf installed successfully via apt-get")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    try:
        # CentOS/RHEL/Fedora
        subprocess.run(["sudo", "yum", "install", "-y", "wkhtmltopdf"], check=True)
        print("✅ wkhtmltopdf installed successfully via yum")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    try:
        # Fedora (newer versions)
        subprocess.run(["sudo", "dnf", "install", "-y", "wkhtmltopdf"], check=True)
        print("✅ wkhtmltopdf installed successfully via dnf")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("❌ Could not install wkhtmltopdf automatically.")
    print("Please install manually:")
    print("Ubuntu/Debian: sudo apt-get install wkhtmltopdf")
    print("CentOS/RHEL: sudo yum install wkhtmltopdf")
    print("Fedora: sudo dnf install wkhtmltopdf")

def install_macos():
    """Install wkhtmltopdf on macOS"""
    print("Installing wkhtmltopdf for macOS...")
    
    try:
        # Try Homebrew first
        subprocess.run(["brew", "install", "wkhtmltopdf"], check=True)
        print("✅ wkhtmltopdf installed successfully via Homebrew")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("❌ Could not install wkhtmltopdf automatically.")
    print("Please install Homebrew first: https://brew.sh/")
    print("Then run: brew install wkhtmltopdf")

def verify_installation():
    """Verify that wkhtmltopdf is installed correctly"""
    print("\nVerifying installation...")
    
    try:
        result = subprocess.run(["wkhtmltopdf", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ wkhtmltopdf is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ wkhtmltopdf not found in PATH")
        
        # Check Windows default location
        if platform.system().lower() == "windows":
            windows_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
            if os.path.exists(windows_path):
                print(f"✅ Found wkhtmltopdf at: {windows_path}")
                print("Django settings.py is configured to use this path.")
                return True
        
        return False

def test_pdf_generation():
    """Test PDF generation with a simple HTML"""
    print("\nTesting PDF generation...")
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test PDF</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>PDF Generation Test</h1>
        <p>If you can see this PDF, wkhtmltopdf is working correctly!</p>
        <p>School Report SaaS PDF system is ready.</p>
    </body>
    </html>
    """
    
    try:
        import pdfkit
        from django.conf import settings
        
        # Configure pdfkit
        if platform.system().lower() == "windows":
            config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
        else:
            config = pdfkit.configuration()
        
        # Generate test PDF
        options = {
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'encoding': 'UTF-8',
            'quiet': ''
        }
        
        pdf_content = pdfkit.from_string(html_content, False, configuration=config, options=options)
        
        # Save test PDF
        with open('test_pdf_generation.pdf', 'wb') as f:
            f.write(pdf_content)
        
        print("✅ PDF generation test successful!")
        print("Test PDF saved as: test_pdf_generation.pdf")
        return True
        
    except ImportError:
        print("❌ pdfkit not installed. Run: pip install pdfkit")
        return False
    except Exception as e:
        print(f"❌ PDF generation test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("School Report SaaS - wkhtmltopdf Installation")
    print("=" * 60)
    
    install_wkhtmltopdf()
    
    print("\n" + "=" * 60)
    
    if verify_installation():
        print("\n🎉 Installation completed successfully!")
        
        # Test PDF generation if pdfkit is available
        try:
            import pdfkit
            test_pdf_generation()
        except ImportError:
            print("\nTo complete the setup, install pdfkit:")
            print("pip install pdfkit")
    else:
        print("\n❌ Installation verification failed.")
        print("Please install wkhtmltopdf manually and ensure it's in your PATH.")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Ensure wkhtmltopdf is installed and working")
    print("2. Run: pip install pdfkit")
    print("3. Test PDF generation in your Django app")
    print("=" * 60)