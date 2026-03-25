from django.test import TestCase, Client
from django.contrib.auth.models import User
from students.models import Student
from scores.models import SubjectResult, ContinuousAssessment, ExamScore
from reports.models import ReportCard
from academic.models import Term

def debug_score_pipeline():
    """Debug the complete score entry to report display pipeline"""
    print("=== TEACHER SCORE TO STUDENT REPORT DEBUG ===\n")
    
    # 1. Check if there are any students
    students = Student.objects.all()
    print(f"1. Total Students in DB: {students.count()}")
    if students.count() == 0:
        print("❌ No students found - create some students first")
        return
    
    student = students.first()
    print(f"   Sample Student: {student.get_full_name()} (ID: {student.student_id})")
    
    # 2. Check if there's a current term
    current_term = Term.objects.filter(is_current=True).first()
    if not current_term:
        current_term = Term.objects.first()
    
    if not current_term:
        print("❌ No terms found - create some terms first")
        return
    
    print(f"   Current Term: {current_term}")
    
    # 3. Check for teacher-entered CA scores
    ca_scores = ContinuousAssessment.objects.filter(student=student, term=current_term)
    print(f"\n2. CA Scores for {student.get_full_name()} in {current_term}:")
    print(f"   Count: {ca_scores.count()}")
    
    if ca_scores.exists():
        for ca in ca_scores:
            print(f"   ✅ {ca.class_subject.subject.name}:")
            print(f"      Task: {ca.task}, Homework: {ca.homework}, Group: {ca.group_work}")
            print(f"      Project: {ca.project_work}, Test: {ca.class_test}")
            print(f"      Total CA: {ca.total_ca_score}")
    else:
        print("   ❌ No CA scores found - teachers need to enter some scores first")
    
    # 4. Check for teacher-entered exam scores  
    exam_scores = ExamScore.objects.filter(student=student, term=current_term)
    print(f"\n3. Exam Scores for {student.get_full_name()} in {current_term}:")
    print(f"   Count: {exam_scores.count()}")
    
    if exam_scores.exists():
        for exam in exam_scores:
            print(f"   ✅ {exam.class_subject.subject.name}: {exam.score}")
    else:
        print("   ❌ No exam scores found - teachers need to enter some scores first")
    
    # 5. Check computed SubjectResult records
    subject_results = SubjectResult.objects.filter(student=student, term=current_term)
    print(f"\n4. Subject Results for {student.get_full_name()} in {current_term}:")
    print(f"   Count: {subject_results.count()}")
    
    if subject_results.exists():
        for sr in subject_results:
            print(f"   ✅ {sr.class_subject.subject.name}:")
            print(f"      CA Score: {sr.ca_score}")
            print(f"      Exam Score: {sr.exam_score}")
            print(f"      Total: {sr.total_score}")
            print(f"      Grade: {sr.grade}")
    else:
        print("   ❌ No subject results found - this is likely the main issue!")
        print("       SubjectResult records should be auto-created when teachers enter scores")
    
    # 6. Check if reports are published
    published_reports = ReportCard.objects.filter(
        student=student,
        term=current_term,
        status='PUBLISHED'
    )
    print(f"\n5. Published Reports for {student.get_full_name()} in {current_term}:")
    print(f"   Count: {published_reports.count()}")
    
    if published_reports.exists():
        for report in published_reports:
            print(f"   ✅ Report {report.id}: {report.status}")
            print(f"      Generated: {report.generated_at}")
            print(f"      Published: {report.published_at}")
    else:
        print("   ❌ No published reports found")
        print("       Teachers need to generate and publish reports after entering scores")
    
    # 7. Final diagnosis  
    print(f"\n=== DIAGNOSIS ===")
    if ca_scores.exists() and exam_scores.exists() and subject_results.exists() and published_reports.exists():
        print("✅ Complete pipeline working - scores should appear in student reports")
    elif ca_scores.exists() and exam_scores.exists() and not subject_results.exists():
        print("❌ Scores entered but SubjectResult not created - check score entry API")
    elif not ca_scores.exists() and not exam_scores.exists():
        print("❌ No scores entered by teachers yet - use teacher score entry page first")
    elif subject_results.exists() and not published_reports.exists():
        print("⚠️  Scores exist but reports not published - student won't see them")
    else:
        print("❌ Partial data - check each step in the pipeline")

if __name__ == "__main__":
    debug_score_pipeline()