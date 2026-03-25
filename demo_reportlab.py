#!/usr/bin/env python
"""
ReportLab PDF Generation Demo
Demonstrates the Windows-compatible PDF generation system
"""

import os
import sys
from datetime import datetime, date, timedelta
from collections import namedtuple

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_sample_data():
    """Create comprehensive sample data for demonstration"""
    print("Creating sample report data...")
    
    # Mock school with all properties
    MockSchool = namedtuple('MockSchool', [
        'name', 'address', 'phone_number', 'motto', 'logo'
    ])
    
    school = MockSchool(
        name="EXCELLENCE INTERNATIONAL SCHOOL",
        address="123 Education Avenue, Academic City, Ghana",
        phone_number="+233 24 123 4567",
        motto="Striving for Excellence in All We Do",
        logo=None
    )
    
    # Mock student with complete information
    MockStudent = namedtuple('MockStudent', [
        'student_id', 'first_name', 'last_name', 'current_class'
    ])
    
    MockClass = namedtuple('MockClass', ['name', 'class_teacher'])
    MockTeacher = namedtuple('MockTeacher', ['first_name', 'last_name'])
    
    teacher = MockTeacher(first_name="Mrs. Sarah", last_name="Johnson")
    current_class = MockClass(name="Basic 9A", class_teacher=teacher)
    
    student = MockStudent(
        student_id="EIS/2024/001",
        first_name="Kwame",
        last_name="Asante",
        current_class=current_class
    )
    
    # Add methods to objects
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    student.get_full_name = get_full_name.__get__(student, MockStudent)
    teacher.get_full_name = get_full_name.__get__(teacher, MockTeacher)
    
    # Mock term and academic year
    MockTerm = namedtuple('MockTerm', ['name', 'academic_year', 'end_date'])
    MockAcademicYear = namedtuple('MockAcademicYear', ['name'])
    
    academic_year = MockAcademicYear(name="2024/2025")
    term = MockTerm(
        name="First Term", 
        academic_year=academic_year,
        end_date=date(2024, 12, 15)
    )
    
    # Mock comprehensive subject results
    MockSubjectResult = namedtuple('MockSubjectResult', [
        'class_subject', 'class_score', 'exam_score', 'total_score', 'grade', 'position'
    ])
    MockClassSubject = namedtuple('MockClassSubject', ['subject'])
    MockSubject = namedtuple('MockSubject', ['name'])
    
    # Realistic Ghanaian JHS subjects with varied performance
    subjects_data = [
        ('English Language', 28, 52, 'B'),
        ('Mathematics', 25, 48, 'C'),
        ('Integrated Science', 30, 55, 'A'),
        ('Social Studies', 27, 50, 'B'),
        ('Religious & Moral Education', 29, 58, 'A'),
        ('Ghanaian Language (Twi)', 26, 49, 'C'),
        ('French', 24, 45, 'C'),
        ('Information Communication Technology', 31, 60, 'A'),
        ('Creative Arts', 28, 53, 'B')
    ]
    
    subject_results = []
    for i, (subject_name, class_score, exam_score, grade) in enumerate(subjects_data):
        subject = MockSubject(name=subject_name)
        class_subject = MockClassSubject(subject=subject)
        
        total_score = class_score + exam_score
        
        result = MockSubjectResult(
            class_subject=class_subject,
            class_score=class_score,
            exam_score=exam_score,
            total_score=total_score,
            grade=grade,
            position=i + 1  # Simple position for demo
        )
        subject_results.append(result)
    
    # Mock term result with calculated values
    MockTermResult = namedtuple('MockTermResult', [
        'total_score', 'average_score', 'class_position', 'total_students', 'teacher_remarks'
    ])
    
    total_scores = sum(result.total_score for result in subject_results)
    average_score = round(total_scores / len(subject_results), 1)
    
    term_result = MockTermResult(
        total_score=total_scores,
        average_score=average_score,
        class_position=8,
        total_students=32,
        teacher_remarks="Kwame has shown consistent improvement this term. "
                       "His performance in Science and ICT is particularly commendable. "
                       "He should focus more on Mathematics and French to achieve better results."
    )
    
    # Create complete context
    context = {
        'school': school,
        'student': student,
        'term': term,
        'subject_results': subject_results,
        'term_result': term_result,
        'class_teacher_name': teacher.get_full_name(),
        'reopening_date': date(2025, 1, 15)
    }
    
    print(f"✅ Sample data created:")
    print(f"   School: {school.name}")
    print(f"   Student: {student.get_full_name()} ({student.student_id})")
    print(f"   Class: {student.current_class.name}")
    print(f"   Term: {term.name} {term.academic_year.name}")
    print(f"   Subjects: {len(subject_results)}")
    print(f"   Average Score: {average_score}%")
    print(f"   Class Position: {term_result.class_position}/{term_result.total_students}")
    
    return context

def generate_demo_pdf():
    """Generate a demonstration PDF using ReportLab"""
    print("\n" + "=" * 60)
    print("GENERATING DEMONSTRATION PDF")
    print("=" * 60)
    
    try:
        # Import the PDF generator
        from reports.pdf_generator import generate_terminal_report_pdf
        
        # Create sample data
        context = create_sample_data()
        
        # Generate PDF
        print("\nGenerating PDF with ReportLab...")
        pdf_content = generate_terminal_report_pdf(context)
        
        if not pdf_content:
            print("❌ PDF generation failed - no content returned")
            return False
        
        # Save the PDF
        output_file = os.path.join(os.path.dirname(__file__), 'demo_terminal_report.pdf')
        with open(output_file, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Demo PDF generated successfully!")
        print(f"   File: {output_file}")
        print(f"   Size: {len(pdf_content):,} bytes")
        print(f"   Contains: School header, student info, grades table, summary")
        
        # Verify PDF structure
        if pdf_content.startswith(b'%PDF'):
            print("✅ Valid PDF format confirmed")
        else:
            print("⚠️  PDF format may be invalid")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import PDF generator: {e}")
        print("Make sure you're running this from the Django project directory")
        return False
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def compare_with_weasyprint():
    """Show the advantages of ReportLab over WeasyPrint on Windows"""
    print("\n" + "=" * 60)
    print("REPORTLAB vs WEASYPRINT COMPARISON")
    print("=" * 60)
    
    print("ReportLab Advantages:")
    print("✅ Native Python library - no external dependencies")
    print("✅ Works perfectly on Windows without additional setup")
    print("✅ No GTK+ or Cairo dependencies required")
    print("✅ Faster PDF generation")
    print("✅ More reliable on Windows systems")
    print("✅ Better memory management")
    print("✅ Programmatic control over PDF layout")
    
    print("\nWeasyPrint Issues on Windows:")
    print("❌ Requires GTK+ installation")
    print("❌ Complex dependency chain")
    print("❌ Often fails on Windows systems")
    print("❌ Requires additional system libraries")
    print("❌ More memory intensive")
    
    print("\nReportLab is the better choice for Windows deployment!")

def show_features():
    """Display the features of the ReportLab implementation"""
    print("\n" + "=" * 60)
    print("REPORTLAB IMPLEMENTATION FEATURES")
    print("=" * 60)
    
    features = [
        "✅ Professional PDF layout with proper spacing",
        "✅ School header with logo support",
        "✅ Student information section",
        "✅ Comprehensive grades table with subjects",
        "✅ Performance summary with statistics",
        "✅ Teacher comments and remarks",
        "✅ Automatic grade calculation",
        "✅ Class position and ranking",
        "✅ Term dates and reopening information",
        "✅ Consistent styling and formatting",
        "✅ Windows-compatible PDF generation",
        "✅ Memory-efficient processing",
        "✅ Error handling and validation"
    ]
    
    for feature in features:
        print(f"  {feature}")

def main():
    """Main demonstration function"""
    print("REPORTLAB PDF GENERATION DEMONSTRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print(f"Python version: {sys.version}")
    
    # Show features
    show_features()
    
    # Generate demo PDF
    success = generate_demo_pdf()
    
    # Show comparison
    compare_with_weasyprint()
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMONSTRATION SUMMARY")
    print("=" * 60)
    
    if success:
        print("🎉 ReportLab PDF generation demonstration completed successfully!")
        print("\nWhat was demonstrated:")
        print("• Complete terminal report PDF generation")
        print("• Professional layout and formatting")
        print("• Windows compatibility")
        print("• Sample student data processing")
        print("• Grade calculations and summaries")
        
        print("\nNext steps:")
        print("1. Run the full test suite: python test_reportlab_pdf.py")
        print("2. Test with real Django data")
        print("3. Deploy to production with confidence")
        
    else:
        print("❌ Demonstration failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Ensure you're in the Django project directory")
        print("2. Check that ReportLab is installed: pip install reportlab")
        print("3. Verify Django settings are configured")
    
    print(f"\nCompleted at: {datetime.now()}")
    return success

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)