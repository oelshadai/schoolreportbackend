#!/usr/bin/env python3
"""
Debug specific student scores - Check what's stored vs what's displayed
Run with: python manage.py shell < debug_binsu_scores.py
"""
from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore, TermResult
from reports.models import ReportCard
from academic.models import Term
from schools.models import ClassSubject

print("=" * 60)
print("DEBUGGING BINSU CHARUITY SCORES")
print("=" * 60)

# Find the student by name (case-insensitive search)
students = Student.objects.filter(
    first_name__icontains='binsu'
).union(
    Student.objects.filter(last_name__icontains='charuity')
).union(
    Student.objects.filter(first_name__icontains='charuity')
).union(
    Student.objects.filter(last_name__icontains='binsu')
)

print(f"\n1. STUDENT SEARCH RESULTS:")
if not students.exists():
    print("   ❌ No students found matching 'binsu' or 'charuity'")
    print("   Searching all students...")
    all_students = Student.objects.all()[:10]
    for s in all_students:
        print(f"   - {s.get_full_name()} (ID: {s.student_id})")
    exit()

for student in students:
    print(f"   - {student.get_full_name()} (ID: {student.student_id})")

# Use the first matching student
student = students.first()
print(f"\n2. ANALYZING: {student.get_full_name()}")

# Get current term
current_term = Term.objects.filter(is_current=True).first()
if not current_term:
    current_term = Term.objects.first()

print(f"   Term: {current_term}")

# Check what should be showing (expected scores)
print(f"\n3. EXPECTED SCORES (from your input):")
expected = {
    'CA': 34,
    'Exam': 30, 
    'Total': 64,
    'Grade': 'C'
}
print(f"   All subjects should show: CA={expected['CA']}, Exam={expected['Exam']}, Total={expected['Total']}, Grade={expected['Grade']}")

# Check actual database scores
print(f"\n4. ACTUAL DATABASE SCORES:")

# CA Scores
ca_scores = ContinuousAssessment.objects.filter(student=student, term=current_term)
print(f"   CA Records: {ca_scores.count()}")
for ca in ca_scores:
    total_ca = ca.total_ca_score
    print(f"   📝 {ca.class_subject.subject.name}: Total CA = {total_ca}")
    print(f"      Components: Task={ca.task}, Homework={ca.homework}, Group={ca.group_work}, Project={ca.project_work}, Test={ca.class_test}")

# Exam Scores  
exam_scores = ExamScore.objects.filter(student=student, term=current_term)
print(f"\n   Exam Records: {exam_scores.count()}")
for exam in exam_scores:
    print(f"   📝 {exam.class_subject.subject.name}: Exam = {exam.score}")

# Subject Results (what the report actually uses)
subject_results = SubjectResult.objects.filter(student=student, term=current_term)
print(f"\n   SubjectResult Records: {subject_results.count()}")
for sr in subject_results:
    print(f"   📊 {sr.class_subject.subject.name}:")
    print(f"      CA: {sr.ca_score} (Expected: {expected['CA']})")
    print(f"      Exam: {sr.exam_score} (Expected: {expected['Exam']})") 
    print(f"      Total: {sr.total_score} (Expected: {expected['Total']})")
    print(f"      Grade: {sr.grade} (Expected: {expected['Grade']})")
    
    # Check for mismatches
    if float(sr.ca_score) != expected['CA']:
        print(f"      ❌ CA MISMATCH: DB shows {sr.ca_score}, should be {expected['CA']}")
    if float(sr.exam_score) != expected['Exam']:
        print(f"      ❌ EXAM MISMATCH: DB shows {sr.exam_score}, should be {expected['Exam']}")
    if float(sr.total_score) != expected['Total']:
        print(f"      ❌ TOTAL MISMATCH: DB shows {sr.total_score}, should be {expected['Total']}")
    if sr.grade != expected['Grade']:
        print(f"      ❌ GRADE MISMATCH: DB shows {sr.grade}, should be {expected['Grade']}")

# Check published reports
print(f"\n5. PUBLISHED REPORTS:")
published_reports = ReportCard.objects.filter(
    student=student,
    term=current_term,
    status='PUBLISHED'
)

print(f"   Published Reports: {published_reports.count()}")
if published_reports.exists():
    report = published_reports.first()
    print(f"   ✅ Report {report.id} is published")
    print(f"      Generated: {report.generated_at}")
    print(f"      Published: {report.published_at}")
else:
    print(f"   ❌ No published reports - student won't see report yet")

# Diagnosis
print(f"\n6. DIAGNOSIS:")
if not ca_scores.exists() and not exam_scores.exists():
    print("❌ ROOT CAUSE: No scores entered for this student")
    print("   SOLUTION: Use teacher score entry to enter the expected scores")

elif ca_scores.exists() and exam_scores.exists() and not subject_results.exists():
    print("❌ ROOT CAUSE: Scores entered but SubjectResult not computed")
    print("   SOLUTION: Check score entry API - SubjectResult should auto-create")

elif subject_results.exists():
    # Check if any scores match expected
    matches = True
    for sr in subject_results:
        if (float(sr.ca_score) != expected['CA'] or 
            float(sr.exam_score) != expected['Exam'] or 
            float(sr.total_score) != expected['Total']):
            matches = False
            break
    
    if matches:
        print("✅ DATABASE SCORES MATCH EXPECTED VALUES")
        print("   Issue might be in report template rendering")
    else:
        print("❌ ROOT CAUSE: Database scores don't match expected values")
        print("   SOLUTION: Correct scores need to be entered via teacher interface")
        
        # Show what needs to be corrected
        print(f"\n   CORRECTIONS NEEDED:")
        for sr in subject_results:
            if float(sr.ca_score) != expected['CA']:
                print(f"   📝 {sr.class_subject.subject.name}: CA {sr.ca_score} → {expected['CA']}")
            if float(sr.exam_score) != expected['Exam']:
                print(f"   📝 {sr.class_subject.subject.name}: Exam {sr.exam_score} → {expected['Exam']}")

print(f"\n7. NEXT STEPS:")
if not subject_results.exists():
    print("1. Teacher should enter scores using the Score Entry page")
    print("2. For each subject, enter:")
    print(f"   - CA components totaling {expected['CA']} marks")
    print(f"   - Exam score of {expected['Exam']} marks")
    print("3. Generate and publish report")
elif not published_reports.exists():
    print("1. Generate report from teacher interface") 
    print("2. Publish the report so student can view it")
else:
    print("1. Check report template rendering")
    print("2. Verify student report viewing endpoint")
    print("3. Clear browser cache and try again")

print("\n" + "=" * 60)
print("BINSU CHARUITY SCORE DEBUG COMPLETE")
print("=" * 60)