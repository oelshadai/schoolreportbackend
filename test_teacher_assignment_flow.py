#!/usr/bin/env python
"""
Test script to verify teacher-class assignment flow
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School, Class, Subject, ClassSubject
from teachers.models import Teacher

User = get_user_model()

def test_teacher_assignment_flow():
    """Test the complete teacher assignment flow"""
    
    print("=== TESTING TEACHER ASSIGNMENT FLOW ===")
    
    # 1. Find or create a school
    school = School.objects.first()
    if not school:
        print("❌ No school found. Please create a school first.")
        return
    
    print(f"✅ Using school: {school.name}")
    
    # 2. Find or create a teacher user
    teacher_user = User.objects.filter(role='TEACHER', school=school).first()
    if not teacher_user:
        print("❌ No teacher user found. Please create a teacher first.")
        return
    
    print(f"✅ Using teacher: {teacher_user.get_full_name()} ({teacher_user.email})")
    
    # 3. Find or create a class
    test_class = Class.objects.filter(school=school).first()
    if not test_class:
        # Create a test class
        test_class = Class.objects.create(
            school=school,
            level='BASIC_1',
            section='A'
        )
        print(f"✅ Created test class: {test_class}")
    else:
        print(f"✅ Using existing class: {test_class}")
    
    # 4. Assign teacher to class
    print(f"\n--- ASSIGNING TEACHER TO CLASS ---")
    print(f"Before assignment:")
    print(f"  Class teacher: {test_class.class_teacher}")
    
    # Assign the teacher
    test_class.class_teacher = teacher_user
    test_class.save()
    
    print(f"After assignment:")
    print(f"  Class teacher: {test_class.class_teacher}")
    
    # 5. Test the teacher assignments endpoint logic
    print(f"\n--- TESTING ASSIGNMENTS ENDPOINT LOGIC ---")
    
    # Get classes where user is class teacher
    class_assignments = Class.objects.filter(
        school=teacher_user.school,
        class_teacher=teacher_user
    )
    
    print(f"Classes where {teacher_user.email} is class teacher: {class_assignments.count()}")
    for cls in class_assignments:
        print(f"  - {cls}")
    
    # Get subject assignments
    subject_assignments = ClassSubject.objects.filter(
        teacher=teacher_user,
        class_instance__school=teacher_user.school
    ).select_related('class_instance', 'subject')
    
    print(f"Subject assignments for {teacher_user.email}: {subject_assignments.count()}")
    for assignment in subject_assignments:
        print(f"  - {assignment.subject.name} in {assignment.class_instance}")
    
    # 6. Test the teacher dashboard endpoint logic
    print(f"\n--- TESTING TEACHER DASHBOARD LOGIC ---")
    
    try:
        teacher_profile = Teacher.objects.get(user=teacher_user)
        assigned_classes = teacher_profile.get_assigned_classes()
        teaching_subjects = teacher_profile.get_teaching_subjects()
        
        print(f"Teacher profile found: {teacher_profile}")
        print(f"Assigned classes via profile: {assigned_classes.count()}")
        print(f"Teaching subjects via profile: {teaching_subjects.count()}")
        
        # Simulate the dashboard response
        classes_data = [{
            'id': c.id,
            'name': str(c),
            'level': c.get_level_display(),
            'students_count': c.students.filter(is_active=True).count()
        } for c in assigned_classes]
        
        subjects_data = [{
            'id': cs.id,
            'subject': cs.subject.name if cs.subject else 'Unknown',
            'class': str(cs.class_instance) if cs.class_instance else 'Unknown',
            'class_id': cs.class_instance.id if cs.class_instance else None
        } for cs in teaching_subjects]
        
        print(f"\nDashboard data:")
        print(f"  Classes: {classes_data}")
        print(f"  Subjects: {subjects_data}")
        
    except Teacher.DoesNotExist:
        print(f"❌ Teacher profile not found for user {teacher_user.email}")
        return
    
    # 7. Create a subject assignment for testing
    print(f"\n--- CREATING SUBJECT ASSIGNMENT ---")
    
    # Find or create a subject
    subject = Subject.objects.first()
    if not subject:
        subject = Subject.objects.create(
            name='Mathematics',
            code='MATH',
            category='BOTH'
        )
        print(f"✅ Created subject: {subject}")
    else:
        print(f"✅ Using subject: {subject}")
    
    # Create class-subject assignment
    class_subject, created = ClassSubject.objects.get_or_create(
        class_instance=test_class,
        subject=subject,
        defaults={'teacher': teacher_user}
    )
    
    if created:
        print(f"✅ Created class-subject assignment: {class_subject}")
    else:
        # Update existing assignment
        class_subject.teacher = teacher_user
        class_subject.save()
        print(f"✅ Updated class-subject assignment: {class_subject}")
    
    # 8. Re-test assignments after subject assignment
    print(f"\n--- RE-TESTING AFTER SUBJECT ASSIGNMENT ---")
    
    class_assignments = Class.objects.filter(
        school=teacher_user.school,
        class_teacher=teacher_user
    )
    
    subject_assignments = ClassSubject.objects.filter(
        teacher=teacher_user,
        class_instance__school=teacher_user.school
    ).select_related('class_instance', 'subject')
    
    print(f"Final class assignments: {class_assignments.count()}")
    print(f"Final subject assignments: {subject_assignments.count()}")
    
    # Simulate the complete assignments endpoint response
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
    
    print(f"\n=== FINAL ASSIGNMENTS ENDPOINT RESPONSE ===")
    import json
    print(json.dumps(results, indent=2))
    
    print(f"\n✅ Teacher assignment flow test completed!")
    print(f"   - Teacher {teacher_user.email} is assigned to {len(results)} classes/subjects")
    print(f"   - The teacher dashboard should now show these assignments")

if __name__ == '__main__':
    test_teacher_assignment_flow()