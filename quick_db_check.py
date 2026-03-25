#!/usr/bin/env python3
"""
Simple database check script to see if scores exist
"""
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

django.setup()

from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore
from reports.models import ReportCard

print("=== DATABASE SCORES CHECK ===")
print(f"Total Students: {Student.objects.count()}")
print(f"Total CA Scores: {ContinuousAssessment.objects.count()}")
print(f"Total Exam Scores: {ExamScore.objects.count()}")
print(f"Total Subject Results: {SubjectResult.objects.count()}")
print(f"Total Report Cards: {ReportCard.objects.count()}")

print("\n=== RECENT ENTRIES ===")
if ContinuousAssessment.objects.exists():
    recent_ca = ContinuousAssessment.objects.order_by('-id').first()
    print(f"Recent CA: {recent_ca.student.get_full_name()} - {recent_ca.class_subject.subject.name} (Total: {recent_ca.total_ca_score})")

if ExamScore.objects.exists():
    recent_exam = ExamScore.objects.order_by('-id').first()
    print(f"Recent Exam: {recent_exam.student.get_full_name()} - {recent_exam.class_subject.subject.name} (Score: {recent_exam.score})")

if SubjectResult.objects.exists():
    recent_result = SubjectResult.objects.order_by('-id').first()
    print(f"Recent Result: {recent_result.student.get_full_name()} - {recent_result.class_subject.subject.name}")
    print(f"  CA: {recent_result.ca_score}, Exam: {recent_result.exam_score}, Total: {recent_result.total_score}")

print("\n=== SAMPLE SUBJECT RESULTS ===")
for sr in SubjectResult.objects.select_related('student', 'class_subject__subject')[:5]:
    print(f"{sr.student.get_full_name()} - {sr.class_subject.subject.name}: CA={sr.ca_score}, Exam={sr.exam_score}, Total={sr.total_score}")