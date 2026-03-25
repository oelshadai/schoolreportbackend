import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User
from schools.models import School, Subject, Class, ClassSubject
from teachers.models import Teacher

def test_teacher_assignment_flow():
    print("=== TESTING TEACHER ASSIGNMENT FLOW ===")
    
    try:
        # Get or create a school
        school, created = School.objects.get_or_create(
            name="Test School",
            defaults={
                'address': '123 Test St',
                'phone': '123-456-7890',
                'email': 'test@school.com'
            }
        )
        print(f"Using school: {school.name}")
        
        # Create a test user for teacher
        user, created = User.objects.get_or_create(
            username='test_teacher',
            defaults={
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@school.com'
            }
        )
        print(f"Created/found user: {user.username}")
        
        # Create a teacher
        teacher, created = Teacher.objects.get_or_create(
            user=user,
            school=school,
            defaults={
                'employee_id': 'T001',
                'phone': '123-456-7890',
                'address': '456 Teacher Ave',
                'qualification': 'Masters in Mathematics',
                'experience_years': 5
            }
        )
        print(f"Created/found teacher: {teacher.user.get_full_name()}")
        
        # Create a subject
        subject, created = Subject.objects.get_or_create(
            name="Mathematics",
            school=school,
            defaults={
                'code': 'MATH101',
                'description': 'Basic Mathematics'
            }
        )
        print(f"Created/found subject: {subject.name}")
        
        # Create a class
        class_obj, created = Class.objects.get_or_create(
            name="Grade 10A",
            school=school,
            defaults={
                'grade_level': 10,
                'section': 'A',
                'capacity': 30
            }
        )
        print(f"Created/found class: {class_obj.name}")
        
        # Create teacher assignment
        assignment, created = TeacherAssignment.objects.get_or_create(
            teacher=teacher,
            subject=subject,
            class_assigned=class_obj,
            defaults={
                'academic_year': '2024-2025',
                'is_class_teacher': True
            }
        )
        
        if created:
            print(f"SUCCESS: Created new assignment")
        else:
            print(f"INFO: Assignment already exists")
            
        print(f"Assignment details:")
        print(f"  Teacher: {assignment.teacher.user.get_full_name()}")
        print(f"  Subject: {assignment.subject.name}")
        print(f"  Class: {assignment.class_assigned.name}")
        print(f"  Academic Year: {assignment.academic_year}")
        print(f"  Is Class Teacher: {assignment.is_class_teacher}")
        
        # Test querying assignments
        all_assignments = TeacherAssignment.objects.filter(teacher=teacher)
        print(f"Total assignments for {teacher.user.get_full_name()}: {all_assignments.count()}")
        
        # Test teacher's subjects
        teacher_subjects = Subject.objects.filter(teacherassignment__teacher=teacher).distinct()
        print(f"Subjects taught by {teacher.user.get_full_name()}:")
        for subj in teacher_subjects:
            print(f"  - {subj.name}")
        
        # Test class assignments
        teacher_classes = Class.objects.filter(teacherassignment__teacher=teacher).distinct()
        print(f"Classes assigned to {teacher.user.get_full_name()}:")
        for cls in teacher_classes:
            print(f"  - {cls.name}")
        
        print("\n=== TEST COMPLETED SUCCESSFULLY ===")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_teacher_assignment_flow()
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
        sys.exit(1)