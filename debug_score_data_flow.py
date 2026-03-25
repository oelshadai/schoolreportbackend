#!/usr/bin/env python3
"""
Debug script to check if teacher-entered scores are properly saved and displayed in student reports.
This script will verify the data flow from teacher score entry to student report display.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore, TermResult
from reports.models import ReportCard
from academic.models import Term, ClassSubject

def show_data_flow():
    """Show the complete data flow from teacher entry to student report"""
    print("=== TEACHER SCORE ENTRY TO STUDENT REPORT DATA FLOW DEBUG ===\n")
    
    # Find a student with some data
    student = Student.objects.filter(is_active=True).first()
    if not student:
        print("❌ No students found in database")
        return
        
    print(f"🎓 Debugging data for student: {student.get_full_name()} (ID: {student.student_id})")
    print(f"📚 Class: {student.current_class}")
    print(f"🏫 School: {student.school.name}\n")
    
    # Get current term
    current_term = Term.objects.filter(is_current=True).first()
    if not current_term:
        current_term = Term.objects.first()
    
    if not current_term:
        print("❌ No terms found in database")
        return
        
    print(f"📅 Current Term: {current_term}\n")
    
    print("=== 1. CONTINUOUS ASSESSMENT SCORES (Teacher Entry) ===")
    ca_scores = ContinuousAssessment.objects.filter(
        student=student,
        term=current_term
    ).select_related('class_subject__subject')
    
    if ca_scores.exists():
        for ca in ca_scores:
            total_ca = ca.total_ca_score
            print(f"📝 {ca.class_subject.subject.name}:")
            print(f"   Task: {ca.task}/10, Homework: {ca.homework}/10, Group: {ca.group_work}/10")
            print(f"   Project: {ca.project_work}/10, Test: {ca.class_test}/10")
            print(f"   → Total CA Score: {total_ca}/50")
    else:
        print("❌ No CA scores found for this student/term")
    
    print("\n=== 2. EXAM SCORES (Teacher Entry) ===")
    exam_scores = ExamScore.objects.filter(
        student=student,
        term=current_term
    ).select_related('class_subject__subject')
    
    if exam_scores.exists():
        for exam in exam_scores:
            print(f"📝 {exam.class_subject.subject.name}: {exam.score}/50")
    else:
        print("❌ No exam scores found for this student/term")
    
    print("\n=== 3. SUBJECT RESULTS (Computed from CA + Exam) ===")
    subject_results = SubjectResult.objects.filter(
        student=student,
        term=current_term
    ).select_related('class_subject__subject')
    
    if subject_results.exists():
        total_ca_sum = 0
        total_exam_sum = 0
        for sr in subject_results:
            print(f"📊 {sr.class_subject.subject.name}:")
            print(f"   CA Score: {sr.ca_score}/50")
            print(f"   Exam Score: {sr.exam_score}/50") 
            print(f"   Total Score: {sr.total_score}/100")
            print(f"   Grade: {sr.grade}")
            total_ca_sum += sr.ca_score
            total_exam_sum += sr.exam_score
        
        print(f"\n📈 TOTALS:")
        print(f"   Total CA: {total_ca_sum}")
        print(f"   Total Exam: {total_exam_sum}")
        print(f"   Grand Total: {total_ca_sum + total_exam_sum}")
    else:
        print("❌ No subject results found for this student/term")
    
    print("\n=== 4. PUBLISHED REPORTS ===")
    published_reports = ReportCard.objects.filter(
        student=student,
        term=current_term,
        status='PUBLISHED'
    )
    
    if published_reports.exists():
        for report in published_reports:
            print(f"📄 Published Report: {report.created_at}")
            print(f"   Status: {report.status}")
    else:
        print("❌ No published reports found for this student/term")
    
    print("\n=== 5. DATA CONSISTENCY CHECK ===")
    
    # Check if CA scores match SubjectResult ca_score
    ca_mismatch = []
    exam_mismatch = []
    
    for sr in subject_results:
        # Find corresponding CA and Exam scores
        ca_obj = ContinuousAssessment.objects.filter(
            student=student,
            term=current_term,
            class_subject=sr.class_subject
        ).first()
        
        exam_obj = ExamScore.objects.filter(
            student=student,
            term=current_term,
            class_subject=sr.class_subject
        ).first()
        
        if ca_obj:
            if float(ca_obj.total_ca_score) != float(sr.ca_score):
                ca_mismatch.append({
                    'subject': sr.class_subject.subject.name,
                    'ca_table': ca_obj.total_ca_score,
                    'subject_result': sr.ca_score
                })
        
        if exam_obj:
            if float(exam_obj.score) != float(sr.exam_score):
                exam_mismatch.append({
                    'subject': sr.class_subject.subject.name,
                    'exam_table': exam_obj.score,
                    'subject_result': sr.exam_score
                })
    
    if ca_mismatch:
        print("⚠️  CA SCORE MISMATCHES FOUND:")
        for mismatch in ca_mismatch:
            print(f"   {mismatch['subject']}: CA table={mismatch['ca_table']}, SubjectResult={mismatch['subject_result']}")
    else:
        print("✅ CA scores consistent between tables")
        
    if exam_mismatch:
        print("⚠️  EXAM SCORE MISMATCHES FOUND:")
        for mismatch in exam_mismatch:
            print(f"   {mismatch['subject']}: Exam table={mismatch['exam_table']}, SubjectResult={mismatch['subject_result']}")
    else:
        print("✅ Exam scores consistent between tables")

def check_mock_data_usage():
    """Check if any part of the system is using mock data"""
    print("\n=== MOCK DATA USAGE CHECK ===")
    
    # Check if there are any mock score entries
    print("🔍 Searching for mock data indicators...")
    
    # Look for any students with obvious mock names
    mock_indicators = ['test', 'mock', 'demo', 'sample', 'fake']
    mock_students = Student.objects.filter(
        first_name__icontains='test'
    ) | Student.objects.filter(
        last_name__icontains='test'
    )
    
    if mock_students.exists():
        print(f"⚠️  Found {mock_students.count()} students with 'test' names:")
        for student in mock_students:
            print(f"   - {student.get_full_name()} ({student.student_id})")
    else:
        print("✅ No obvious mock/test students found")
    
    # Check for uniform score patterns (indicating mock data)
    print("\n🔍 Checking for uniform score patterns...")
    uniform_scores = SubjectResult.objects.filter(
        ca_score=25, exam_score=25  # Common mock score pattern
    )
    
    if uniform_scores.exists():
        print(f"⚠️  Found {uniform_scores.count()} results with uniform 25/25 scores (possible mock data)")
    else:
        print("✅ No obvious uniform score patterns found")

def check_latest_entries():
    """Check the most recent score entries"""
    print("\n=== LATEST SCORE ENTRIES CHECK ===")
    
    latest_ca = ContinuousAssessment.objects.order_by('-id').first()
    latest_exam = ExamScore.objects.order_by('-id').first()
    latest_subject_result = SubjectResult.objects.order_by('-id').first()
    
    print("📅 Most Recent Entries:")
    if latest_ca:
        print(f"   Last CA Entry: {latest_ca.student.get_full_name()} - {latest_ca.class_subject.subject.name} (Total: {latest_ca.total_ca_score})")
    
    if latest_exam:
        print(f"   Last Exam Entry: {latest_exam.student.get_full_name()} - {latest_exam.class_subject.subject.name} (Score: {latest_exam.score})")
    
    if latest_subject_result:
        print(f"   Last Subject Result: {latest_subject_result.student.get_full_name()} - {latest_subject_result.class_subject.subject.name}")
        print(f"     CA: {latest_subject_result.ca_score}, Exam: {latest_subject_result.exam_score}, Total: {latest_subject_result.total_score}")

if __name__ == '__main__':
    show_data_flow()
    check_mock_data_usage()
    check_latest_entries()
    print("\n=== DEBUG COMPLETED ===")