#!/usr/bin/env python
"""
Test script to verify logo display in report templates
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from schools.models import School
from reports.utils import get_media_base_url, get_absolute_media_url
from django.test import RequestFactory

def test_logo_display():
    """Test logo URL generation and display"""
    print("Testing logo display functionality...")
    
    # Get a school with a logo
    school = School.objects.filter(logo__isnull=False).first()
    
    if not school:
        print("❌ No school with logo found. Please upload a logo first.")
        return False
    
    print(f"✅ Found school: {school.name}")
    print(f"✅ Logo field: {school.logo}")
    print(f"✅ Logo URL: {school.logo.url}")
    
    # Test media URL base generation
    factory = RequestFactory()
    request = factory.get('/')
    
    media_base = get_media_base_url(request)
    print(f"✅ Media base URL: {media_base}")
    
    # Test absolute URL generation
    absolute_url = get_absolute_media_url(school.logo, request)
    print(f"✅ Absolute logo URL: {absolute_url}")
    
    # Test template context
    context = {
        'school': school,
        'media_url_base': media_base
    }
    
    # Simulate template rendering
    template_logo_url = f"{media_base}{school.logo.url}"
    print(f"✅ Template logo URL: {template_logo_url}")
    
    # Test if file exists
    try:
        if school.logo.path and os.path.exists(school.logo.path):
            print(f"✅ Logo file exists at: {school.logo.path}")
            file_size = os.path.getsize(school.logo.path)
            print(f"✅ Logo file size: {file_size} bytes")
        else:
            print(f"❌ Logo file not found at: {school.logo.path}")
    except Exception as e:
        print(f"❌ Error checking logo file: {e}")
    
    return True

def test_template_rendering():
    """Test template rendering with logo"""
    print("\nTesting template rendering...")
    
    from django.template.loader import render_to_string
    from django.test import RequestFactory
    from reports.views import ReportCardViewSet
    
    # Get a school with a logo
    school = School.objects.filter(logo__isnull=False).first()
    
    if not school:
        print("❌ No school with logo found.")
        return False
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/')
    
    # Create sample data
    viewset = ReportCardViewSet()
    viewset.request = request
    
    try:
        sample_data = viewset._create_sample_report_data(school)
        print("✅ Sample data created successfully")
        
        # Get media URL base
        from reports.utils import get_media_base_url
        media_url_base = get_media_base_url(request)
        
        context = {
            'school': school,
            'student': sample_data['student'],
            'term': sample_data['term'],
            'subject_results': sample_data['subject_results'],
            'term_result': sample_data['term_result'],
            'attendance': sample_data['attendance'],
            'behaviour': sample_data['behaviour'],
            'empty_rows': range(5),
            'is_preview': True,
            'media_url_base': media_url_base
        }
        
        # Try to render template
        html_content = render_to_string('reports/terminal_report_template.html', context)
        
        # Check if logo URL is in the rendered HTML
        logo_url = f"{media_url_base}{school.logo.url}"
        if logo_url in html_content:
            print(f"✅ Logo URL found in rendered HTML: {logo_url}")
        else:
            print(f"❌ Logo URL not found in rendered HTML")
            print(f"Expected: {logo_url}")
            # Show a snippet of the HTML around logo references
            import re
            logo_matches = re.findall(r'<img[^>]*src="[^"]*"[^>]*alt="School Logo"[^>]*>', html_content)
            if logo_matches:
                print(f"Found logo img tags: {logo_matches}")
            else:
                print("No logo img tags found")
        
        print("✅ Template rendered successfully")
        return True
        
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LOGO DISPLAY TEST")
    print("=" * 50)
    
    success = test_logo_display()
    if success:
        test_template_rendering()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)