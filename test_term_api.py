#!/usr/bin/env python
"""
Test the term selection API endpoint
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from schools.models import School, Term
from schools.serializers import TermSerializer

def test_term_api():
    """Test the term API response format"""
    print("Testing Term API Response...")
    print("=" * 40)
    
    school = School.objects.first()
    if not school:
        print("No schools found!")
        return
    
    print(f"Testing with school: {school.name}")
    
    # Get terms for this school
    terms = Term.objects.filter(academic_year__school=school)
    
    print(f"Found {terms.count()} terms")
    
    for term in terms:
        serializer = TermSerializer(term)
        data = serializer.data
        print(f"\nTerm: {term.name}")
        print(f"  ID: {data['id']}")
        print(f"  Name: {data['name']}")
        print(f"  Display Name: {data['display_name']}")
        print(f"  Academic Year: {data['academic_year_name']}")
        print(f"  Is Current: {data['is_current']}")
        
        # Test the mapping logic from frontend
        term_number = '1' if term.name == 'FIRST' else \
                     '2' if term.name == 'SECOND' else \
                     '3' if term.name == 'THIRD' else ''
        print(f"  Frontend Display: {term_number} ({'1st' if term_number == '1' else '2nd' if term_number == '2' else '3rd' if term_number == '3' else 'Unknown'} Term)")
    
    print("\n" + "=" * 40)
    print("Term API Test Complete!")

if __name__ == '__main__':
    test_term_api()