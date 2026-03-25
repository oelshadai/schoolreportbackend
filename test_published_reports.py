#!/usr/bin/env python3
"""
Quick test for the published_reports endpoint
"""
import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from reports.models import ReportCard
from schools.models import Class, Term
from django.contrib.auth.models import User

print("=" * 60)
print("TESTING PUBLISHED REPORTS ENDPOINT")
print("=" * 60)

try:
    # Check if we can query published reports
    published_reports = ReportCard.objects.filter(status='PUBLISHED')
    print(f"✅ Found {published_reports.count()} published reports")
    
    # Check if Class model works
    teacher_classes = Class.objects.all()[:5]
    print(f"✅ Found {teacher_classes.count()} classes")
    
    # Test the specific query issue that was failing
    if teacher_classes.exists():
        class_ids = teacher_classes.values_list('id', flat=True)
        print(f"✅ Class IDs: {list(class_ids)}")
        
        test_query = ReportCard.objects.filter(
            student__current_class_id__in=class_ids,
            status='PUBLISHED'
        )
        print(f"✅ Query with current_class_id__in works: {test_query.count()} results")
        
        # Test select_related
        test_query_related = test_query.select_related('student', 'term')
        print(f"✅ Select related works: {test_query_related.count()} results")
        
        # Test accessing the data
        for report in test_query_related[:3]:
            try:
                data = {
                    'id': report.id,
                    'student_name': report.student.get_full_name(),
                    'student_id': report.student.student_id,
                    'report_code': report.report_code,
                    'published_at': report.published_at,
                    'total_score': report.total_score,
                    'average_score': report.average_score,
                    'position': report.position or 0,
                    'term_name': report.term.name if report.term else 'Unknown Term'
                }
                print(f"✅ Report data access works: {data['student_name']}")
            except Exception as e:
                print(f"❌ Error accessing report data: {e}")
                break
    else:
        print("⚠️  No classes found")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)