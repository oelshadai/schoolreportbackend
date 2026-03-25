#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from schools.models import School, Class

def create_test_classes():
    try:
        # Get the first school
        school = School.objects.first()
        if not school:
            print("No school found. Please create a school first.")
            return
        
        print(f"Creating classes for school: {school.name}")
        
        # Create basic classes
        classes_to_create = [
            ('BASIC_1', 'A'),
            ('BASIC_1', 'B'),
            ('BASIC_2', 'A'),
            ('BASIC_3', 'A'),
            ('BASIC_4', 'A'),
            ('BASIC_5', 'A'),
            ('BASIC_6', 'A'),
            ('BASIC_7', 'A'),
            ('BASIC_8', 'A'),
            ('BASIC_9', 'A'),
        ]
        
        created_count = 0
        for level, section in classes_to_create:
            class_obj, created = Class.objects.get_or_create(
                school=school,
                level=level,
                section=section,
                defaults={'capacity': 30}
            )
            if created:
                created_count += 1
                print(f"Created: {class_obj}")
            else:
                print(f"Already exists: {class_obj}")
        
        print(f"\nCreated {created_count} new classes")
        print(f"Total classes in school: {Class.objects.filter(school=school).count()}")
        
    except Exception as e:
        print(f"Error creating classes: {e}")

if __name__ == "__main__":
    create_test_classes()