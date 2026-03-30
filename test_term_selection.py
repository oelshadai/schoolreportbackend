#!/usr/bin/env python
"""
Test script to verify term selection functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from schools.models import School, AcademicYear, Term

def test_term_selection():
    """Test if terms are properly set up and can be selected"""
    print("Testing Term Selection Functionality...")
    print("=" * 50)
    
    schools = School.objects.all()
    print(f"Found {schools.count()} schools")
    
    for school in schools:
        print(f"\nSchool: {school.name}")
        print(f"Current Academic Year: {school.current_academic_year}")
        print(f"Current Term ID: {school.current_term_id}")
        
        # Get all terms for this school
        academic_years = AcademicYear.objects.filter(school=school)
        print(f"Academic Years: {academic_years.count()}")
        
        for ay in academic_years:
            print(f"  - {ay.name} (Current: {ay.is_current})")
            terms = Term.objects.filter(academic_year=ay)
            for term in terms:
                current_marker = " <- CURRENT" if school.current_term_id == term.id else ""
                print(f"    * {term.name} (ID: {term.id}){current_marker}")
        
        # Test term display mapping
        if school.current_term:
            current_term = school.current_term
            term_display = "1st" if current_term.name == "FIRST" else \
                          "2nd" if current_term.name == "SECOND" else \
                          "3rd" if current_term.name == "THIRD" else current_term.name
            print(f"Current Term Display: {term_display} Term")
        else:
            print("No current term set!")
    
    print("\n" + "=" * 50)
    print("Term Selection Test Complete!")

if __name__ == '__main__':
    test_term_selection()