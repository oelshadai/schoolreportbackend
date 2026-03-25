import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from students.models import Student
from assignments.models import Assignment, StudentAssignment
from schools.models import Class

def test_student_assignments():
    print("Testing student assignment access...")
    
    # Find a student
    student_user = User.objects.filter(role='STUDENT').first()
    if not student_user:
        print("No student found")
        return
    
    try:
        student = Student.objects.get(user=student_user)
        print(f"Student: {student.get_full_name()} (ID: {student.id})")
        print(f"Student Class: {student.current_class}")
        
        if not student.current_class:
            print("Student has no class assigned")
            return
        
        # Find published assignments for student's class
        published_assignments = Assignment.objects.filter(
            class_instance=student.current_class,
            status='PUBLISHED'
        )
        
        print(f"Published assignments for class: {published_assignments.count()}")
        
        # Create StudentAssignment records for new assignments
        for assignment in published_assignments:
            student_assignment, created = StudentAssignment.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )
            if created:
                print(f"Created StudentAssignment for: {assignment.title}")
        
        # Get student assignments
        student_assignments = StudentAssignment.objects.filter(
            student=student,
            assignment__status='PUBLISHED'
        )
        
        print(f"Student assignments: {student_assignments.count()}")
        
        for sa in student_assignments:
            print(f"- {sa.assignment.title} (Status: {sa.status})")
        
    except Student.DoesNotExist:
        print("Student profile not found for user")
    
    print("Test completed!")

if __name__ == '__main__':
    test_student_assignments()