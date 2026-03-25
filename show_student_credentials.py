#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Setup Django from backend directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth.models import User, Group
from students.models import Student
from reports.models import ReportCard

def show_student_credentials():
    """Show student login credentials"""
    print("=== STUDENT LOGIN CREDENTIALS ===")
    
    students_with_reports = Student.objects.filter(
        id__in=ReportCard.objects.filter(status='PUBLISHED').values_list('student_id', flat=True)
    )
    
    print(f"Students with published reports: {students_with_reports.count()}")
    
    for student in students_with_reports:
        print(f"\n🎓 {student.first_name} {student.last_name}")
        print(f"   📧 Guardian Email: {student.guardian_email or 'Not set'}")
        print(f"   🆔 Student ID: {student.student_id}")
        if student.user:
            print(f"   👤 Usuario: {student.user.username}")
            print(f"   🔑 Reset password with: {student.user.username}")
            
            # Check groups
            groups = [g.name for g in student.user.groups.all()]
            print(f"   👥 Groups: {groups}")
            
            # Check if active
            print(f"   ✅ Active: {student.user.is_active}")
            
            # Check published reports
            reports = ReportCard.objects.filter(student=student, status='PUBLISHED')
            print(f"   📊 Published reports: {reports.count()}")
            for report in reports:
                print(f"       - {report.term.get_name_display()} (Published: {report.published_at.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print("   ❌ No User account linked!")
    
    print("\n=== ALL STUDENTS IN 'Students' GROUP ===")
    students_group = Group.objects.get(name='Students')
    group_users = students_group.user_set.all()
    
    for user in group_users:
        try:
            student = Student.objects.get(user=user)
            reports_count = ReportCard.objects.filter(student=student, status='PUBLISHED').count()
            print(f"👤 {user.username} → {student.first_name} {student.last_name} ({reports_count} published reports)")
        except Student.DoesNotExist:
            print(f"👤 {user.username} → ❌ No linked Student record")

if __name__ == "__main__":
    show_student_credentials()