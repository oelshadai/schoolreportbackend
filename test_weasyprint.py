#!/usr/bin/env python
"""
Test script to verify WeasyPrint PDF generation works correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

def test_weasyprint_pdf():
    """Test WeasyPrint PDF generation with sample HTML"""
    try:
        from weasyprint import HTML
        
        # Simple test HTML
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @page { size: A4; margin: 15mm; }
                body { font-family: Arial, sans-serif; }
                .test-content { padding: 20px; border: 1px solid #000; }
            </style>
        </head>
        <body>
            <div class="test-content">
                <h1>WeasyPrint Test</h1>
                <p>This is a test to verify WeasyPrint is working correctly.</p>
                <p>If you can see this PDF, the implementation is working!</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_content = HTML(string=test_html).write_pdf()
        
        # Save test PDF
        with open('weasyprint_test.pdf', 'wb') as f:
            f.write(pdf_content)
        
        print("✅ WeasyPrint test successful!")
        print(f"✅ Generated test PDF: {len(pdf_content)} bytes")
        print("✅ Test file saved as: weasyprint_test.pdf")
        return True
        
    except ImportError as e:
        print(f"❌ WeasyPrint not available: {e}")
        return False
    except Exception as e:
        print(f"❌ WeasyPrint test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing WeasyPrint PDF generation...")
    test_weasyprint_pdf()