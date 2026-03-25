#!/usr/bin/env python3
"""
Debug assignment field name issue
"""
import os
import sys
import django
import sqlite3

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.conf import settings

def check_assignments_table():
    """Check assignments table schema"""
    db_path = settings.DATABASES['default']['NAME']
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get assignments table schema
        cursor.execute("PRAGMA table_info(assignments)")
        columns = cursor.fetchall()
        
        print("Columns in assignments table:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Check for class-related fields
        column_names = [col[1] for col in columns]
        
        class_fields = [name for name in column_names if 'class' in name.lower()]
        print(f"\nClass-related fields: {class_fields}")
        
        # Check actual data
        cursor.execute("SELECT id, title, class_instance_id FROM assignments LIMIT 5")
        assignments = cursor.fetchall()
        
        print(f"\nSample assignments:")
        for assignment in assignments:
            print(f"  ID: {assignment[0]}, Title: {assignment[1]}, Class: {assignment[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_assignments_table()