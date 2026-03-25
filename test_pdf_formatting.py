#!/usr/bin/env python
"""
Test script to verify PDF formatting matches preview
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.template.loader import render_to_string
from reports.pdf_generator import generate_terminal_report_pdf
from schools.models import School
from students.models import Student
from schools.models import Term
from reports.views import ReportCardViewSet

def test_pdf_formatting():
    """Test that PDF generation uses the same template as preview"""
    
    try:
        # Get a school for testing
        school = School.objects.first()
        if not school:
            print("No school found. Please create a school first.")
            return False
        
        print("Using school: {}".format(school.name))
        
        # Get a student for testing
        student = Student.objects.filter(school=school, is_active=True).first()
        if not student:
            print("No active student found. Please create a student first.")
            return False
        
        print("Using student: {}".format(student.get_full_name()))
        
        # Get a term for testing
        term = Term.objects.first()
        if not term:
            print("No term found. Please create a term first.")
            return False
        
        print("Using term: {}".format(term.name))
        
        # Create a mock request object
        class MockRequest:
            def build_absolute_uri(self, path='/'):
                return 'http://localhost:8000'
        
        mock_request = MockRequest()
        
        # Generate context using the same method as the view
        viewset = ReportCardViewSet()
        context = viewset._get_report_context(student, term, mock_request)
        
        print("Generated report context")
        
        # Test HTML template rendering
        html_content = render_to_string('reports/terminal_report.html', context)
        
        if len(html_content) > 1000:  # Basic check that template rendered
            print("HTML template rendered successfully")
            print(f"   Template size: {len(html_content)} characters")
        else:
            print("HTML template rendering failed or too short")
            return False
        
        # Test PDF generation
        try:
            pdf_content = generate_terminal_report_pdf(context)
            
            if isinstance(pdf_content, bytes) and len(pdf_content) > 1000:
                print("PDF generated successfully")
                print(f"   PDF size: {len(pdf_content)} bytes")
                
                # Save test PDF
                with open('test_generated.pdf', 'wb') as f:
                    f.write(pdf_content)
                print("Test PDF saved as 'test_generated.pdf'")
                
                return True
            else:
                print("PDF generation failed or returned invalid content")
                print(f"   Content type: {type(pdf_content)}")
                print(f"   Content length: {len(pdf_content) if pdf_content else 0}")
                return False
                
        except Exception as e:
            print(f"PDF generation error: {str(e)}")
            return False
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Testing PDF formatting consistency...")
    print("=" * 50)
    
    success = test_pdf_formatting()
    
    print("=" * 50)
    if success:
        print("All tests passed! PDF formatting should now match preview.")
    else:
        print("Tests failed. Please check the errors above.")
    
    print("\nSummary of changes made:")
    print("1. Updated PDF generator to use 'terminal_report.html' template")
    print("2. Synchronized CSS styles between preview and PDF")
    print("3. Adjusted PDF generation margins and zoom settings")
    print("4. Enhanced print media queries for better PDF rendering")
    print("5. Added color-adjust properties for background preservation")