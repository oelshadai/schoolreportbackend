#!/usr/bin/env python
"""
Fix Admin School Association
This script checks if school admin users have a school assigned and fixes them if not.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth import get_user_model
from schools.models import School

User = get_user_model()

def check_and_fix_admin_schools():
    """Check all school admin users and ensure they have schools assigned"""
    
    print("=" * 60)
    print("Admin School Association Check")
    print("=" * 60)
    
    # Get all school admins
    admins = User.objects.filter(role='SCHOOL_ADMIN')
    
    if not admins.exists():
        print("No school admin users found.")
        return
    
    print(f"\nFound {admins.count()} school admin user(s):\n")
    
    admins_without_school = []
    
    for admin in admins:
        has_school = admin.school is not None
        status = "✓ Has School" if has_school else "✗ NO SCHOOL"
        school_name = admin.school.name if has_school else "N/A"
        
        print(f"  ID: {admin.id}")
        print(f"  Email: {admin.email}")
        print(f"  Name: {admin.first_name} {admin.last_name}")
        print(f"  Status: {status}")
        print(f"  School: {school_name}")
        print("-" * 40)
        
        if not has_school:
            admins_without_school.append(admin)
    
    if not admins_without_school:
        print("\n✓ All school admins have schools assigned!")
        return
    
    print(f"\n⚠ Found {len(admins_without_school)} admin(s) without school assignment.")
    
    # Show available schools
    schools = School.objects.all()
    if not schools.exists():
        print("\n✗ No schools exist in the database. Please create a school first.")
        return
    
    print("\nAvailable schools:")
    for i, school in enumerate(schools, 1):
        print(f"  {i}. {school.name} (ID: {school.id})")
    
    # Ask user to fix
    print("\nWould you like to fix the admin(s) without schools?")
    choice = input("Enter 'y' to fix, or 'n' to skip: ").strip().lower()
    
    if choice != 'y':
        print("Skipping fix.")
        return
    
    for admin in admins_without_school:
        print(f"\nFixing admin: {admin.email}")
        
        if schools.count() == 1:
            # Auto-assign if only one school
            school = schools.first()
            print(f"  Auto-assigning to: {school.name}")
        else:
            # Ask which school
            school_choice = input(f"  Enter school number (1-{schools.count()}) for {admin.email}: ").strip()
            try:
                school_idx = int(school_choice) - 1
                school = list(schools)[school_idx]
            except (ValueError, IndexError):
                print("  Invalid choice, skipping this admin.")
                continue
        
        admin.school = school
        admin.save()
        print(f"  ✓ Assigned {admin.email} to {school.name}")
    
    print("\n✓ Fix complete!")


def list_all_users_with_schools():
    """List all users and their school assignments"""
    print("\n" + "=" * 60)
    print("All Users and Their Schools")
    print("=" * 60)
    
    users = User.objects.all().order_by('role', 'email')
    
    for user in users:
        school_info = user.school.name if user.school else "NO SCHOOL"
        print(f"  {user.role:15} | {user.email:30} | {school_info}")


if __name__ == '__main__':
    check_and_fix_admin_schools()
    
    print("\n" + "=" * 60)
    show_all = input("\nShow all users? (y/n): ").strip().lower()
    if show_all == 'y':
        list_all_users_with_schools()
