#!/usr/bin/env python
"""
Comprehensive test runner for both fixes
Run this to test teacher creation and logo display fixes
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

def run_all_tests():
    print("🚀 Running Comprehensive Tests for Deployment Fixes")
    print("=" * 60)
    
    # Import test functions
    try:
        from test_teacher_creation_fix import test_teacher_creation
        from test_logo_display_fix import test_logo_display, test_template_rendering
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    
    results = []
    
    # Test 1: Teacher Creation
    print("\n1️⃣ TESTING: Teacher Creation Fix")
    print("-" * 40)
    try:
        teacher_result = test_teacher_creation()
        results.append(("Teacher Creation", teacher_result))
    except Exception as e:
        print(f"❌ Teacher Creation Test Failed: {e}")
        results.append(("Teacher Creation", False))
    
    # Test 2: Logo Display
    print("\n2️⃣ TESTING: Logo Display Fix")
    print("-" * 40)
    try:
        logo_result = test_logo_display()
        template_result = test_template_rendering()
        logo_overall = logo_result and template_result
        results.append(("Logo Display", logo_overall))
    except Exception as e:
        print(f"❌ Logo Display Test Failed: {e}")
        results.append(("Logo Display", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} : {status}")
        if not passed:
            all_passed = False
    
    print("-" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED - READY FOR DEPLOYMENT! 🚀")
        print("\n✅ Safe to push to GitHub and redeploy")
        print("✅ Teacher creation will work without school field")
        print("✅ Logos will display correctly in reports")
    else:
        print("💥 SOME TESTS FAILED - DO NOT DEPLOY YET! ⚠️")
        print("\n❌ Fix failing tests before deployment")
        print("❌ Check error messages above")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)