#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.db import connection

def check_assignments_table():
    with connection.cursor() as cursor:
        # Get table schema
        cursor.execute("PRAGMA table_info(assignments);")
        columns = cursor.fetchall()
        
        print("Assignments table schema:")
        print("=" * 50)
        for column in columns:
            print(f"Column: {column[1]}, Type: {column[2]}, Null: {column[3]}, Default: {column[4]}")
        
        # Check if start_date exists
        column_names = [col[1] for col in columns]
        if 'start_date' in column_names:
            print("\n✅ start_date column exists!")
        else:
            print("\n❌ start_date column is missing!")

if __name__ == "__main__":
    check_assignments_table()