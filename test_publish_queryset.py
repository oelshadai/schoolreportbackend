#!/usr/bin/env python
"""
Test script to verify the publish endpoint queryset filtering issue
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from assignments.models import Assignment
from students.models import Student
from schools.models import School, Class, Term, AcademicYear

User = get_user_model()

def test_publish_queryset_issue():
    """Test the queryset filtering issue in publish endpoint"""
    
    # Create or get school
    school, _ = School.objects.get_or_create(
        email="test@school.com",
        defaults={
            "name": "Test School",
            "address": "123 Test St",
            "location": "Test City",
            "phone_number": "123-456-7890",
        }
    )
    
    # Create or get academic year and term
    academic_year, _ = AcademicYear.objects.get_or_create(
        school=school,
        name="2024",
        defaults={
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=365)).date()
        }
    )
    
    term, _ = Term.objects.get_or_create(
        academic_year=academic_year,
        name="FIRST",
        defaults={
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=90)).date()
        }
    )
    
    # Create or get class
    test_class, _ = Class.objects.get_or_create(
        school=school,
        level="BASIC_5",
        section="A"
    )
    
    # Create or get teacher user (assignment creator)
    teacher_user, _ = User.objects.get_or_create(
        email="teacher@test.com",
        defaults={
            "password": "testpass123",
            "first_name": "John",
            "last_name": "Teacher",
            "role": "TEACHER"
        }
    )
    
    # Create or get admin user (different from creator)
    admin_user, _ = User.objects.get_or_create(
        email="admin@test.com",
        defaults={
            "password": "testpass123",
            "first_name": "Admin",
            "last_name": "User",
            "role": "SCHOOL_ADMIN"
        }
    )
    
    # Create assignment by teacher
    assignment = Assignment.objects.create(
        title="Test Assignment",
        description="This is a test assignment",
        assignment_type="HOMEWORK",
        class_instance=test_class,
        term=term,
        created_by=teacher_user,  # Created by teacher
        due_date=timezone.now() + timedelta(days=7),
        max_score=100,
        status="DRAFT"
    )
    
    print(f"Created assignment {assignment.id} by teacher {teacher_user.email}")
    
    # Test 1: Teacher can publish their own assignment
    client = Client()
    client.force_login(teacher_user)
    
    response = client.post(f'/api/assignments/assignments/{assignment.id}/publish/')
    print(f"Teacher publish response: {response.status_code}")
    if response.status_code != 200:
        print(f"Teacher publish error: {response.content}")
    
    # Reset assignment to DRAFT
    assignment.status = "DRAFT"
    assignment.published_at = None
    assignment.save()
    
    # Test 2: Admin tries to publish teacher's assignment (this should work but might fail due to queryset filtering)
    client.force_login(admin_user)
    
    response = client.post(f'/api/assignments/assignments/{assignment.id}/publish/')
    print(f"Admin publish response: {response.status_code}")
    if response.status_code != 200:
        print(f"Admin publish error: {response.content}")
        
        # Check if it's a 404 (queryset filtering issue)
        if response.status_code == 404:
            print("ISSUE CONFIRMED: Admin gets 404 due to queryset filtering")
            print("The get_queryset() method filters by created_by=request.user")
            print("This prevents admins from accessing assignments created by teachers")
        else:
            print(f"Different error: {response.json()}")
    else:
        print("SUCCESS: Admin can publish teacher's assignment")
    
    # Test 3: Check what assignments each user can see
    print("\n--- Queryset Analysis ---")
    
    # Teacher's queryset
    from assignments.views import AssignmentViewSet
    viewset = AssignmentViewSet()
    viewset.request = type('Request', (), {'user': teacher_user})()
    viewset.action = 'list'  # Not publish action
    teacher_queryset = viewset.get_queryset()
    print(f"Teacher can see {teacher_queryset.count()} assignments")
    
    # Admin's queryset (non-publish action)
    viewset.request.user = admin_user
    admin_queryset = viewset.get_queryset()
    print(f"Admin can see {admin_queryset.count()} assignments (non-publish)")
    
    # Admin's queryset (publish action)
    viewset.action = 'publish'
    admin_publish_queryset = viewset.get_queryset()
    print(f"Admin can see {admin_publish_queryset.count()} assignments (publish action)")
    
    print("\n--- Summary ---")
    print("If admin gets 404 when trying to publish, the issue is in get_queryset()")
    print("The current implementation filters by created_by for non-publish actions")
    print("But allows broader access for publish actions with permission checks")

if __name__ == "__main__":
    test_publish_queryset_issue()