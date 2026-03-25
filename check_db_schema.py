#!/usr/bin/env python3
"""
Check database schema for student_assignments table
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

def check_table_schema():
    """Check the actual database schema"""
    db_path = settings.DATABASES['default']['NAME']
    
    print(f"Database path: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(student_assignments)")
        columns = cursor.fetchall()
        
        print("\nColumns in student_assignments table:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # Check if current_attempt_started_at exists
        column_names = [col[1] for col in columns]
        if 'current_attempt_started_at' in column_names:
            print("\n✓ current_attempt_started_at column exists")
        else:
            print("\n✗ current_attempt_started_at column is MISSING")
            
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_table_schema()