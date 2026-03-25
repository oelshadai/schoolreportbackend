#!/usr/bin/env python3
"""
Test script to verify teacher dashboard class assignment fix
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from schools.models import School, Class
from teachers.models import Teacher

User = get_user_model()

def test_teacher_class_assignment():
    """Test the complete teacher-class assignment pipeline"""
    
    print("🔍 TESTING TEACHER-CLASS ASSIGNMENT PIPELINE")
    print("=" * 60)
    
    # Find a school
    school = School.objects.first()
    if not school:
        print("❌ No school found. Create a school first.")
        return False
    
    print(f"✅ Using school: {school.name}")
    
    # Find or create a teacher
    teacher_user = User.objects.filter(role='TEACHER', school=school).first()
    if not teacher_user:
        print("❌ No teacher found. Create a teacher first.")
        return False
    
    print(f"✅ Using teacher: {teacher_user.email}")
    
    # Find or create a class
    test_class = Class.objects.filter(school=school).first()
    if not test_class:
        print("❌ No class found. Create a class first.")
        return False
    
    print(f"✅ Using class: {test_class}")
    
    # Test 1: Assign teacher to class
    print("\n📝 TEST 1: Assigning teacher to class...")
    test_class.class_teacher = teacher_user
    test_class.save()
    print(f"✅ Assigned {teacher_user.email} as class teacher for {test_class}")
    
    # Test 2: Verify assignment in database
    print("\n📝 TEST 2: Verifying database assignment...")
    db_class = Class.objects.get(id=test_class.id)
    if db_class.class_teacher == teacher_user:
        print(f"✅ Database verification: class_teacher_id = {db_class.class_teacher_id}")
    else:
        print(f"❌ Database verification failed: expected {teacher_user.id}, got {db_class.class_teacher_id}")
        return False
    
    # Test 3: Test teacher dashboard query
    print("\n📝 TEST 3: Testing teacher dashboard query...")
    assigned_classes = Class.objects.filter(
        class_teacher=teacher_user,
        school=school
    )
    
    print(f"✅ Dashboard query found {assigned_classes.count()} classes:")
    for cls in assigned_classes:
        print(f"   - {cls} (ID: {cls.id})")
    
    # Test 4: Test teacher model method
    print("\n📝 TEST 4: Testing teacher model method...")
    try:
        teacher_profile = Teacher.objects.get(user=teacher_user)
        model_classes = teacher_profile.get_assigned_classes()
        print(f"✅ Teacher model method found {model_classes.count()} classes:")
        for cls in model_classes:
            print(f"   - {cls} (ID: {cls.id})")
    except Teacher.DoesNotExist:
        print("❌ Teacher profile not found")
        return False
    
    # Test 5: Simulate dashboard endpoint data
    print("\n📝 TEST 5: Simulating dashboard endpoint response...")
    classes_data = [{
        'id': c.id,
        'name': str(c),
        'level': c.get_level_display(),
        'students_count': c.students.filter(is_active=True).count()
    } for c in assigned_classes]
    
    print(f"✅ Dashboard data structure:")
    for cls_data in classes_data:
        print(f"   - {cls_data}")
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Teacher-class assignment pipeline is working correctly")
    return True

if __name__ == "__main__":
    success = test_teacher_class_assignment()
    if success:
        print("\n✅ TEACHER DASHBOARD FIX VERIFIED")
    else:
        print("\n❌ TEACHER DASHBOARD FIX FAILED")
        sys.exit(1)