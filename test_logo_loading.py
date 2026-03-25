#!/usr/bin/env python
"""
Test script to verify logo loading in reports
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from schools.models import School
from reports.image_loader import ReportImageLoader

def test_logo_loading():
    """Test logo loading functionality"""
    print("Testing logo loading...")
    
    # Get first school with a logo
    schools_with_logos = School.objects.exclude(logo='').exclude(logo__isnull=True)
    
    if not schools_with_logos.exists():
        print("No schools with logos found. Creating test school...")
        # Create a test school with logo
        school = School.objects.create(
            name="Test School",
            address="123 Test Street",
            location="Test City",
            phone_number="0123456789",
            email="test@school.edu",
            logo="school_logos/loggo.jfif"  # Use existing logo file
        )
    else:
        school = schools_with_logos.first()
    
    print(f"Testing with school: {school.name}")
    print(f"Logo field: {school.logo}")
    
    if school.logo:
        print(f"Logo URL: {school.logo.url}")
        
        # Test direct file access
        try:
            print(f"Logo path: {school.logo.path}")
            print(f"File exists: {os.path.exists(school.logo.path)}")
        except ValueError as e:
            print(f"Cannot get file path: {e}")
        
        # Test image loader
        reader, width, height = ReportImageLoader.get_image_reader(school.logo, 2, 2)
        
        if reader:
            print(f"✅ Logo loaded successfully! Dimensions: {width:.2f}x{height:.2f} inches")
        else:
            print("❌ Failed to load logo")
            
            # Try to create placeholder
            placeholder_reader, p_width, p_height = ReportImageLoader.create_placeholder_image(2, 2, "LOGO")
            if placeholder_reader:
                print(f"✅ Placeholder created: {p_width}x{p_height} inches")
            else:
                print("❌ Failed to create placeholder")
    else:
        print("No logo file found")

if __name__ == "__main__":
    test_logo_loading()