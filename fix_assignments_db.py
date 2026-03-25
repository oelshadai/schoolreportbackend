#!/usr/bin/env python
"""
Fix assignments database schema mismatch
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.db import connection
from assignments.models import Assignment

def check_and_fix_schema():
    """Check and fix assignments table schema"""
    with connection.cursor() as cursor:
        # Check current table schema
        cursor.execute("PRAGMA table_info(assignments)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("Current assignments table columns:")
        for col in columns:
            print(f"  {col[1]} - {col[2]}")
        
        # Check if max_attempts column exists
        if 'max_attempts' not in column_names:
            print("\nAdding missing max_attempts column...")
            cursor.execute("ALTER TABLE assignments ADD COLUMN max_attempts INTEGER DEFAULT 1")
            print("[OK] Added max_attempts column")
        
        # Check if instructions column exists
        if 'instructions' not in column_names:
            print("\nAdding missing instructions column...")
            cursor.execute("ALTER TABLE assignments ADD COLUMN instructions TEXT DEFAULT ''")
            print("[OK] Added instructions column")
        
        # Check if class_subject_id column exists
        if 'class_subject_id' not in column_names:
            print("\nAdding missing class_subject_id column...")
            cursor.execute("ALTER TABLE assignments ADD COLUMN class_subject_id INTEGER")
            print("[OK] Added class_subject_id column")
        
        # Check if term_id column exists
        if 'term_id' not in column_names:
            print("\nAdding missing term_id column...")
            cursor.execute("ALTER TABLE assignments ADD COLUMN term_id INTEGER")
            print("[OK] Added term_id column")
        
        print("\nDatabase schema updated successfully!")
        
        # Now test querying assignments
        try:
            assignments = Assignment.objects.all()
            print(f"\n[OK] Successfully queried {assignments.count()} assignments")
            
            for assignment in assignments[:3]:
                print(f"  - {assignment.title} (Status: {assignment.status})")
                
        except Exception as e:
            print(f"\n[ERROR] Error querying assignments: {e}")

if __name__ == "__main__":
    check_and_fix_schema()