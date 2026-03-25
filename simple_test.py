import os
import django
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User
from schools.models import School, Class
from teachers.models import Teacher

def test_teacher_assignment():
    print("=== TESTING TEACHER ASSIGNMENT FLOW ===")
    
    # Get or create a school
    school = School.objects.first()
    if not school:
        print("ERROR: No school found. Please create a school first.")
        return
    
    print(f"Using school: {school.name}")
    
    # Get or create a class
    test_class = Class.objects.filter(school=school).first()
    if not test_class:
        test_class = Class.objects.create(
            name="Test Class 1A",
            school=school,
            academic_year="2024"
        )
        print(f"Created test class: {test_class.name}")
    else:
        print(f"Using existing class: {test_class.name}")
    
    # Create a test user for teacher
    username = "test_teacher_001"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@school.com'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing user: {user.username}")
    
    # Create or get teacher
    teacher, created = Teacher.objects.get_or_create(
        user=user,
        school=school,
        defaults={
            'employee_id': 'EMP001',
            'phone': '+1234567890',
            'subject_specialization': 'Mathematics',
            'qualification': 'Bachelor of Education',
            'hire_date': '2024-01-01'
        }
    )
    
    if created:
        print(f"Created teacher: {teacher.user.get_full_name()}")
    else:
        print(f"Using existing teacher: {teacher.user.get_full_name()}")
    
    # Test teacher assignment
    assignment, created = TeacherAssignment.objects.get_or_create(
        teacher=teacher,
        class_assigned=test_class,
        defaults={
            'subject': 'Mathematics',
            'is_class_teacher': True,
            'academic_year': '2024'
        }
    )
    
    if created:
        print(f"Created assignment: {teacher.user.get_full_name()} -> {test_class.name}")
    else:
        print(f"Assignment already exists: {teacher.user.get_full_name()} -> {test_class.name}")
    
    # Verify the assignment
    assignments = TeacherAssignment.objects.filter(teacher=teacher)
    print(f"Total assignments for {teacher.user.get_full_name()}: {assignments.count()}")
    
    for assign in assignments:
        print(f"  - {assign.class_assigned.name} ({assign.subject}) - Class Teacher: {assign.is_class_teacher}")
    
    print("\n=== TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_teacher_assignment()