#!/usr/bin/env python
"""
Test script for PDF generation system
Verifies that wkhtmltopdf is installed and PDF generation works correctly
"""

import os
import sys
import subprocess

def test_wkhtmltopdf_installation():
    """Test if wkhtmltopdf is installed and accessible"""
    print("=" * 60)
    print("Testing wkhtmltopdf Installation")
    print("=" * 60)
    
    # Determine expected path based on OS
    if os.name == 'nt':  # Windows
        wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    else:  # Linux/Mac
        wkhtmltopdf_path = "wkhtmltopdf"
    
    try:
        result = subprocess.run(
            [wkhtmltopdf_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ wkhtmltopdf is installed")
            print(f"   Version: {result.stdout.strip()}")
            print(f"   Path: {wkhtmltopdf_path}")
            return True
        else:
            print("❌ wkhtmltopdf found but returned error")
            print(f"   Error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ wkhtmltopdf NOT found")
        print(f"   Expected path: {wkhtmltopdf_path}")
        print("\n   Installation instructions:")
        print("   Windows: Download from https://wkhtmltopdf.org/downloads.html")
        print("   Linux: sudo apt-get install wkhtmltopdf")
        print("   Mac: brew install wkhtmltopdf")
        return False
    except Exception as e:
        print(f"❌ Error testing wkhtmltopdf: {e}")
        return False


def test_pdfkit_installation():
    """Test if pdfkit Python package is installed"""
    print("\n" + "=" * 60)
    print("Testing pdfkit Python Package")
    print("=" * 60)
    
    try:
        import pdfkit
        print("✅ pdfkit is installed")
        print(f"   Version: {pdfkit.__version__ if hasattr(pdfkit, '__version__') else 'Unknown'}")
        return True
    except ImportError:
        print("❌ pdfkit NOT installed")
        print("   Install with: pip install pdfkit")
        return False


def test_django_settings():
    """Test if Django settings are configured correctly"""
    print("\n" + "=" * 60)
    print("Testing Django Settings")
    print("=" * 60)
    
    try:
        # Add Django project to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
        import django
        django.setup()
        
        from django.conf import settings
        
        if hasattr(settings, 'WKHTMLTOPDF_CMD'):
            print("✅ WKHTMLTOPDF_CMD is configured")
            print(f"   Path: {settings.WKHTMLTOPDF_CMD}")
            
            # Check if path exists
            if os.path.exists(settings.WKHTMLTOPDF_CMD):
                print("   ✅ Path exists")
            else:
                print("   ⚠️  Path does not exist - please verify installation")
            
            return True
        else:
            print("❌ WKHTMLTOPDF_CMD not found in settings")
            print("   Please add to settings.py:")
            print("   WKHTMLTOPDF_CMD = r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Django settings: {e}")
        return False


def test_pdf_generation():
    """Test actual PDF generation"""
    print("\n" + "=" * 60)
    print("Testing PDF Generation")
    print("=" * 60)
    
    try:
        import pdfkit
        from django.conf import settings
        
        # Simple HTML test
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #333; }
                .box { border: 2px solid #000; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>Test Terminal Report</h1>
            <div class="box">
                <p>This is a test PDF generation.</p>
                <p>If you can see this, PDF generation is working correctly!</p>
            </div>
        </body>
        </html>
        """
        
        # Configure pdfkit
        config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_CMD)
        
        options = {
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'encoding': 'UTF-8',
            'quiet': ''
        }
        
        # Generate PDF
        pdf_content = pdfkit.from_string(
            html_content,
            False,
            configuration=config,
            options=options
        )
        
        # Save test PDF
        test_pdf_path = os.path.join(os.path.dirname(__file__), 'test_pdf_output.pdf')
        with open(test_pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        print("✅ PDF generation successful")
        print(f"   Test PDF saved to: {test_pdf_path}")
        print(f"   File size: {len(pdf_content)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PDF GENERATION SYSTEM TEST")
    print("=" * 60)
    
    results = {
        'wkhtmltopdf': test_wkhtmltopdf_installation(),
        'pdfkit': test_pdfkit_installation(),
        'django_settings': test_django_settings(),
        'pdf_generation': test_pdf_generation()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - PDF generation is ready!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Preview reports in iframe (uses terminal_report.html)")
        print("2. Download PDF (uses SAME template and context)")
        print("3. PDF will render identically to preview")
    else:
        print("⚠️  SOME TESTS FAILED - Please fix issues above")
        print("=" * 60)
        print("\nRefer to PDF_GENERATION_SETUP.md for detailed instructions")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
