#!/usr/bin/env python3
"""
Complete diagnostic script for teacher scores to student reports pipeline.
Run with: python manage.py shell < complete_debug.py
"""
from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore, TermResult
from reports.models import ReportCard
from academic.models import Term
from schools.models import ClassSubject

print("=" * 60)
print("COMPLETE TEACHER SCORE → STUDENT REPORT DIAGNOSTIC")
print("=" * 60)

# Step 1: Basic data check
students = Student.objects.all()
print(f"\n1. DATABASE OVERVIEW")
print(f"   Students: {students.count()}")
print(f"   CA Scores: {ContinuousAssessment.objects.count()}")  
print(f"   Exam Scores: {ExamScore.objects.count()}")
print(f"   Subject Results: {SubjectResult.objects.count()}")
print(f"   Report Cards: {ReportCard.objects.count()}")

if students.count() == 0:
    print("\n❌ FATAL: No students in database")
    exit()

# Step 2: Pick a student to analyze
student = students.first()
print(f"\n2. ANALYZING STUDENT: {student.get_full_name()} (ID: {student.student_id})")

# Step 3: Find current term
current_term = Term.objects.filter(is_current=True).first()
if not current_term:
    current_term = Term.objects.first()

if not current_term:
    print("❌ FATAL: No terms in database")
    exit()

print(f"   Term: {current_term}")
print(f"   School: {student.school.name}")

# Step 4: Check if student has subjects assigned
subjects = ClassSubject.objects.filter(class_instance=student.current_class) if student.current_class else []
print(f"   Assigned Subjects: {subjects.count()}")

if subjects.count() == 0:
    print("❌ ISSUE: Student has no subjects assigned to their class")
else:
    for i, subject in enumerate(subjects[:3], 1):
        print(f"     {i}. {subject.subject.name} (Teacher: {subject.teacher.get_full_name() if subject.teacher else 'None'})")

# Step 5: Check teacher-entered scores
print(f"\n3. TEACHER SCORE ENTRY STATUS")

ca_scores = ContinuousAssessment.objects.filter(student=student, term=current_term)
exam_scores = ExamScore.objects.filter(student=student, term=current_term)

print(f"   CA Scores Entered: {ca_scores.count()}")
print(f"   Exam Scores Entered: {exam_scores.count()}")

if ca_scores.exists():
    ca = ca_scores.first()
    print(f"   ✅ Sample CA: {ca.class_subject.subject.name} = {ca.total_ca_score}")
else:
    print("   ❌ No CA scores - teachers haven't entered any yet")

if exam_scores.exists():
    exam = exam_scores.first()
    print(f"   ✅ Sample Exam: {exam.class_subject.subject.name} = {exam.score}")
else:
    print("   ❌ No exam scores - teachers haven't entered any yet")

# Step 6: Check computed subject results
print(f"\n4. COMPUTED SUBJECT RESULTS")
subject_results = SubjectResult.objects.filter(student=student, term=current_term)
print(f"   Subject Results: {subject_results.count()}")

if subject_results.exists():
    sr = subject_results.first()
    print(f"   ✅ Sample Result: {sr.class_subject.subject.name}")
    print(f"      CA: {sr.ca_score}, Exam: {sr.exam_score}, Total: {sr.total_score}")
    print(f"      Grade: {sr.grade}")
else:
    print("   ❌ No subject results computed")
    if ca_scores.exists() or exam_scores.exists():
        print("      ERROR: Scores exist but SubjectResult not created!")
        print("      This indicates a bug in the score entry process")

# Step 7: Check report generation  
print(f"\n5. REPORT GENERATION STATUS")
all_reports = ReportCard.objects.filter(student=student, term=current_term)
published_reports = all_reports.filter(status='PUBLISHED')

print(f"   Total Reports: {all_reports.count()}")
print(f"   Published Reports: {published_reports.count()}")

if all_reports.exists():
    report = all_reports.first()
    print(f"   Latest Report Status: {report.status}")
    print(f"   Generated At: {report.generated_at}")
    print(f"   Published At: {report.published_at}")
    
    if report.status == 'PUBLISHED':
        print("   ✅ Report is published - students can view it")
    else:
        print("   ⚠️  Report exists but not published - students cannot view it")
else:
    print("   ❌ No reports generated for this student")

# Step 8: Final diagnosis
print(f"\n6. DIAGNOSIS & NEXT STEPS")
print("=" * 40)

if not ca_scores.exists() and not exam_scores.exists():
    print("❌ ROOT CAUSE: No scores entered by teachers")
    print("   SOLUTION: Teachers need to use the score entry page to enter scores")
    print("   PATH: Teacher Dashboard → Score Entry → Select student/subject → Enter CA & Exam scores")
    
elif ca_scores.exists() and exam_scores.exists() and not subject_results.exists():
    print("❌ ROOT CAUSE: Scores entered but SubjectResult not computed")  
    print("   SOLUTION: Check the score entry API for bugs")
    print("   DEBUG: Look at /scores/manage/enter_scores/ endpoint")
    
elif subject_results.exists() and not all_reports.exists():
    print("❌ ROOT CAUSE: Scores computed but no reports generated")
    print("   SOLUTION: Teachers need to generate reports")
    print("   PATH: Teacher Dashboard → Reports → Generate Report for this student")
    
elif all_reports.exists() and not published_reports.exists():
    print("❌ ROOT CAUSE: Reports generated but not published")
    print("   SOLUTION: Teachers need to publish the reports")
    print("   PATH: Teacher Dashboard → Reports → Publish Report")
    
elif published_reports.exists():
    print("✅ PIPELINE COMPLETE: All steps working correctly")
    print("   Student should be able to view their report with scores")
    print("   If scores still appear empty, check template rendering issues")
    
else:
    print("❓ PARTIAL PIPELINE: Mixed state detected")
    print("   Review each step above to identify the break point")

print(f"\n7. QUICK FIXES")
print("=" * 20)

if subject_results.exists() and all_reports.exists() and not published_reports.exists():
    print("⚡ QUICK FIX: Auto-publish the existing report")
    report = all_reports.first() 
    if report.status == 'GENERATED':
        report.publish_report()
        print(f"   ✅ Published report {report.id}")
    else:
        print(f"   ❌ Cannot publish - report status is {report.status}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)