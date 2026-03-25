#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School, Class, Subject, ClassSubject
from teachers.models import Teacher

User = get_user_model()

def test_teacher_assignments():
    """Test teacher assignments endpoint functionality"""
    print("=== Testing Teacher Assignments ===")
    
    # Find a teacher user
    teachers = User.objects.filter(role='TEACHER')
    if not teachers.exists():
        print("❌ No teachers found in database")
        return
    
    teacher_user = teachers.first()
    print(f"✅ Found teacher: {teacher_user.email}")
    
    # Check if teacher has school
    if not hasattr(teacher_user, 'school') or not teacher_user.school:
        print("❌ Teacher has no school assigned")
        return
    
    print(f"✅ Teacher school: {teacher_user.school.name}")
    
    # Check class assignments
    class_assignments = Class.objects.filter(
        school=teacher_user.school,
        class_teacher=teacher_user
    )
    print(f"📚 Form teacher for {class_assignments.count()} classes:")
    for cls in class_assignments:
        print(f"   - {cls}")
    
    # Check subject assignments
    subject_assignments = ClassSubject.objects.filter(
        teacher=teacher_user,
        class_instance__school=teacher_user.school
    )
    print(f"📖 Subject teacher for {subject_assignments.count()} subjects:")
    for assignment in subject_assignments:
        print(f"   - {assignment.subject.name} in {assignment.class_instance}")
    
    # Test the API logic
    results = []
    
    # Add class assignments
    for cls in class_assignments:
        results.append({
            'id': f'class_{cls.id}',
            'type': 'form_class',
            'class': {
                'id': cls.id,
                'name': str(cls),
                'level': cls.level,
                'section': cls.section or ''
            },
            'subject': None,
            'assignment_count': 0
        })
    
    # Add subject assignments
    for assignment in subject_assignments:
        results.append({
            'id': assignment.id,
            'type': 'subject_class',
            'class': {
                'id': assignment.class_instance.id,
                'name': str(assignment.class_instance),
                'level': assignment.class_instance.level,
                'section': assignment.class_instance.section or ''
            },
            'subject': {
                'id': assignment.subject.id,
                'name': assignment.subject.name
            },
            'assignment_count': 0
        })
    
    print(f"\n🎯 API would return {len(results)} assignments:")
    for result in results:
        if result['type'] == 'form_class':
            print(f"   📚 Form Teacher: {result['class']['name']}")
        else:
            print(f"   📖 Subject Teacher: {result['subject']['name']} in {result['class']['name']}")
    
    return results

def create_test_assignments():
    """Create test assignments if none exist"""
    print("\n=== Creating Test Assignments ===")
    
    # Get or create a school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'address': 'Test Address',
            'location': 'Test Location',
            'phone_number': '1234567890',
            'email': 'test@school.com'
        }
    )
    if created:
        print(f"✅ Created school: {school.name}")
    else:
        print(f"✅ Using existing school: {school.name}")
    
    # Get or create a teacher
    teacher_user, created = User.objects.get_or_create(
        email='teacher@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Teacher',
            'role': 'TEACHER',
            'school': school
        }
    )
    if created:
        teacher_user.set_password('password123')
        teacher_user.save()
        print(f"✅ Created teacher user: {teacher_user.email}")
    else:
        # Ensure teacher has school
        if not teacher_user.school:
            teacher_user.school = school
            teacher_user.save()
        print(f"✅ Using existing teacher: {teacher_user.email}")
    
    # Create teacher profile if it doesn't exist
    teacher_profile, created = Teacher.objects.get_or_create(
        user=teacher_user,
        defaults={
            'school': school,
            'employee_id': 'T001',
            'hire_date': '2024-01-01'
        }
    )
    if created:
        print(f"✅ Created teacher profile for: {teacher_user.email}")
    
    # Create a test class
    test_class, created = Class.objects.get_or_create(
        school=school,
        level='BASIC_1',
        section='A',
        defaults={
            'class_teacher': teacher_user,
            'capacity': 30
        }
    )
    if created:
        print(f"✅ Created class: {test_class}")
    elif not test_class.class_teacher:
        test_class.class_teacher = teacher_user
        test_class.save()
        print(f"✅ Assigned teacher to class: {test_class}")
    
    # Create a test subject
    subject, created = Subject.objects.get_or_create(
        name='Mathematics',
        defaults={
            'code': 'MATH',
            'category': 'PRIMARY'
        }
    )
    if created:
        print(f"✅ Created subject: {subject.name}")
    
    # Create class-subject assignment
    class_subject, created = ClassSubject.objects.get_or_create(
        class_instance=test_class,
        subject=subject,
        defaults={
            'teacher': teacher_user
        }
    )
    if created:
        print(f"✅ Created class-subject assignment: {class_subject}")
    elif not class_subject.teacher:
        class_subject.teacher = teacher_user
        class_subject.save()
        print(f"✅ Assigned teacher to subject: {class_subject}")
    
    print(f"\n🎯 Test data created successfully!")
    return teacher_user

if __name__ == '__main__':
    try:
        # First try to test existing data
        results = test_teacher_assignments()
        
        # If no assignments found, create test data
        if not results:
            print("\n⚠️  No assignments found. Creating test data...")
            teacher_user = create_test_assignments()
            print("\n=== Testing Again with New Data ===")
            test_teacher_assignments()
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()