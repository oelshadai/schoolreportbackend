#!/usr/bin/env python
"""
Test assignment endpoints
"""
import os
import sys
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School, Class
from assignments.models import Assignment

User = get_user_model()

def test_assignment_endpoints():
    """Test assignment API endpoints"""
    
    # Get test teacher
    try:
        teacher = User.objects.get(email="teacher@test.com")
        print(f"Found teacher: {teacher.email}")
    except User.DoesNotExist:
        print("Teacher not found. Run create_test_teacher.py first.")
        return
    
    # Get test class
    try:
        class_instance = Class.objects.get(level="BASIC_5", section="A")
        print(f"Found class: {class_instance}")
    except Class.DoesNotExist:
        print("Class not found. Run create_test_teacher.py first.")
        return
    
    # Check assignments
    assignments = Assignment.objects.filter(
        class_instance=class_instance,
        created_by=teacher
    )
    
    print(f"\nAssignments found: {assignments.count()}")
    for assignment in assignments:
        print(f"- {assignment.title} ({assignment.status}) - Created by: {assignment.created_by.email}")
    
    # Check if assignments are visible in VClass
    print(f"\nClass teacher: {class_instance.class_teacher}")
    print(f"Teacher ID: {teacher.id}")
    print(f"Class teacher ID: {class_instance.class_teacher.id if class_instance.class_teacher else 'None'}")
    
    # Check class subjects
    from schools.models import ClassSubject
    class_subjects = ClassSubject.objects.filter(class_instance=class_instance)
    print(f"\nClass subjects: {class_subjects.count()}")
    for cs in class_subjects:
        print(f"- {cs.subject.name} taught by: {cs.teacher.email if cs.teacher else 'No teacher assigned'}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_assignment_endpoints()