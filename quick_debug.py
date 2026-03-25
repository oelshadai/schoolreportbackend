#!/usr/bin/env python3
"""
Direct Django shell commands to debug scores
Run this inside Django shell: python manage.py shell < debug_commands.py
"""
from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore
from reports.models import ReportCard
from academic.models import Term

print("=== QUICK DJANGO DB CHECK ===")

print(f"Students: {Student.objects.count()}")
print(f"CA Scores: {ContinuousAssessment.objects.count()}")  
print(f"Exam Scores: {ExamScore.objects.count()}")
print(f"Subject Results: {SubjectResult.objects.count()}")
print(f"Report Cards: {ReportCard.objects.count()}")

if Student.objects.exists():
    student = Student.objects.first()
    current_term = Term.objects.filter(is_current=True).first() or Term.objects.first()
    
    print(f"\nStudent: {student.get_full_name()}")
    print(f"Term: {current_term}")
    
    if current_term:
        ca_count = ContinuousAssessment.objects.filter(student=student, term=current_term).count()
        exam_count = ExamScore.objects.filter(student=student, term=current_term).count()
        sr_count = SubjectResult.objects.filter(student=student, term=current_term).count()
        
        print(f"CA for this student/term: {ca_count}")
        print(f"Exam for this student/term: {exam_count}")
        print(f"SubjectResults for this student/term: {sr_count}")
        
        if sr_count > 0:
            sr = SubjectResult.objects.filter(student=student, term=current_term).first()
            print(f"Sample SubjectResult: {sr.class_subject.subject.name}")
            print(f"  ca_score: {sr.ca_score}")
            print(f"  exam_score: {sr.exam_score}")
            print(f"  total_score: {sr.total_score}")

print("\n=== DIAGNOSIS ===")
if SubjectResult.objects.count() == 0:
    print("❌ NO SUBJECT RESULTS - This is why reports are empty!")
    print("Teachers need to use the score entry system to create these records")
else:
    print("✅ Subject results exist - check if reports are published")