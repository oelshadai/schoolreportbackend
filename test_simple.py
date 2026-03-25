import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from accounts.models import User
from assignments.models import Assignment
from schools.models import Class

def test_assignment_filtering():
    print("Testing assignment filtering...")
    
    # Find teacher
    teacher = User.objects.filter(email='teacher@test.com').first()
    if not teacher:
        print("No teacher found")
        return
    
    print(f"Teacher: {teacher.email} (ID: {teacher.id})")
    
    # Find assignments by user ID
    assignments_by_id = Assignment.objects.filter(created_by=teacher)
    print(f"Assignments by user ID: {assignments_by_id.count()}")
    
    # Find assignments by email
    assignments_by_email = Assignment.objects.filter(created_by__email=teacher.email)
    print(f"Assignments by email: {assignments_by_email.count()}")
    
    # List all assignments
    for assignment in assignments_by_id:
        print(f"- {assignment.title} (Status: {assignment.status})")
    
    print("Test completed!")

if __name__ == '__main__':
    test_assignment_filtering()