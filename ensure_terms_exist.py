#!/usr/bin/env python
"""
Ensure all schools have academic years and terms set up
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.utils import timezone
from datetime import date
from schools.models import School, AcademicYear, Term

def setup_terms_for_all_schools():
    """Setup academic years and terms for all schools"""
    current_year = timezone.now().year
    schools = School.objects.all()
    
    print(f"Setting up terms for {schools.count()} schools...")
    
    for school in schools:
        print(f"\nProcessing {school.name}...")
        
        # Create current academic year
        academic_year_name = f"{current_year}/{current_year + 1}"
        academic_year, created = AcademicYear.objects.get_or_create(
            school=school,
            name=academic_year_name,
            defaults={
                'start_date': date(current_year, 9, 1),
                'end_date': date(current_year + 1, 7, 31),
                'is_current': True
            }
        )
        
        if created:
            print(f"  [+] Created academic year: {academic_year_name}")
        else:
            print(f"  [-] Academic year exists: {academic_year_name}")
        
        # Create terms
        terms_data = [
            {
                'name': 'FIRST',
                'start_date': date(current_year, 9, 1),
                'end_date': date(current_year, 12, 15),
                'total_days': 90,
                'is_current': True
            },
            {
                'name': 'SECOND', 
                'start_date': date(current_year + 1, 1, 8),
                'end_date': date(current_year + 1, 4, 15),
                'total_days': 85,
                'is_current': False
            },
            {
                'name': 'THIRD',
                'start_date': date(current_year + 1, 4, 22),
                'end_date': date(current_year + 1, 7, 31),
                'total_days': 80,
                'is_current': False
            }
        ]
        
        for term_data in terms_data:
            term, created = Term.objects.get_or_create(
                academic_year=academic_year,
                name=term_data['name'],
                defaults=term_data
            )
            
            if created:
                print(f"  [+] Created term: {term_data['name']}")
            else:
                print(f"  [-] Term exists: {term_data['name']}")
        
        # Update school's current academic year and term if not set
        if not school.current_academic_year:
            school.current_academic_year = academic_year_name
            school.save()
            print(f"  [+] Updated school current academic year")
        
        # Set current term if not set
        if not school.current_term:
            first_term = Term.objects.filter(
                academic_year=academic_year,
                name='FIRST'
            ).first()
            if first_term:
                school.current_term = first_term
                school.save()
                print(f"  [+] Set current term to FIRST")
    
    print(f"\n[SUCCESS] Successfully setup academic years and terms for all schools!")

if __name__ == '__main__':
    setup_terms_for_all_schools()