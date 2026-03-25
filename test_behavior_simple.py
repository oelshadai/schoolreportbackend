#!/usr/bin/env python
"""
Simple test to verify the behavior endpoint without Django test client
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student, Behaviour
from students.serializers import BehaviourSerializer
from schools.models import School
from django.contrib.auth import get_user_model

User = get_user_model()

def test_behavior_models():
    print("=== Testing Behavior Models and Serializers ===")
    
    # Test model creation
    try:
        school, _ = School.objects.get_or_create(
            name="Test School",
            defaults={'address': 'Test', 'phone': '123', 'email': 'test@test.com'}
        )
        
        student, _ = Student.objects.get_or_create(
            student_id="TEST001",
            defaults={
                'first_name': 'Test',
                'last_name': 'Student',
                'school': school,
                'gender': 'M',
                'date_of_birth': '2010-01-01',
                'guardian_name': 'Test Guardian',
                'guardian_phone': '123456789',
                'guardian_address': 'Test Address',
                'admission_date': '2023-01-01'
            }
        )
        
        # Create term first
        from schools.models import Term, AcademicYear
        academic_year, _ = AcademicYear.objects.get_or_create(
            year='2024',
            defaults={'school': school, 'is_current': True}
        )
        term, _ = Term.objects.get_or_create(
            name='First Term',
            defaults={
                'academic_year': academic_year,
                'start_date': '2024-01-01',
                'end_date': '2024-04-30'
            }
        )
        
        # Create behavior record with correct fields
        behavior = Behaviour.objects.create(
            student=student,
            term=term,
            conduct='EXCELLENT',
            attitude='GOOD',
            punctuality='EXCELLENT',
            interest='READING_WRITING',
            class_teacher_remarks='Test remarks',
            promoted_to='Next Class'
        )
        
        print(f"✓ Created behavior record: {behavior.id}")
        
        # Test serializer
        serializer = BehaviourSerializer(behavior)
        print(f"✓ Serializer data: {serializer.data}")
        
        # Test queryset
        behaviors = Behaviour.objects.filter(student__school=school)
        print(f"✓ Found {behaviors.count()} behavior records")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_behavior_choices():
    print("\n=== Testing Behavior Choices ===")
    
    try:
        from students.models import Behaviour
        
        # Test all choice fields
        choices = {
            'conduct': Behaviour.CONDUCT_CHOICES,
            'attitude': Behaviour.ATTITUDE_CHOICES,
            'punctuality': Behaviour.CONDUCT_CHOICES,
            'interest': Behaviour.INTEREST_CHOICES,
        }
        
        print(f"✓ Conduct choices: {dict(Behaviour.CONDUCT_CHOICES)}")
        print(f"✓ Attitude choices: {dict(Behaviour.ATTITUDE_CHOICES)}")
        print(f"✓ Interest choices: {dict(Behaviour.INTEREST_CHOICES)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    success1 = test_behavior_models()
    success2 = test_behavior_choices()
    
    if success1 and success2:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")