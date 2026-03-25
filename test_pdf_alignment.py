#!/usr/bin/env python3
"""
Test script to verify PDF alignment and watermark centering
"""
import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.template.loader import render_to_string
from django.http import HttpRequest
from reports.pdf_generator import generate_terminal_report_pdf
from schools.models import School
from students.models import Student
from schools.models import Term, AcademicYear
import tempfile
import webbrowser

def test_pdf_alignment():
    """Test PDF generation and alignment"""
    print("Testing PDF alignment and watermark centering...")
    
    try:
        # Get a school for testing
        school = School.objects.first()
        if not school:
            print("No school found. Please create a school first.")
            return False
            
        print(f"Using school: {school.name}")
        
        # Create mock request
        request = HttpRequest()
        request.user = school.users.first() if school.users.exists() else None
        
        # Create sample context data
        from collections import namedtuple
        
        # Mock student
        MockStudent = namedtuple('MockStudent', ['get_full_name', 'student_id', 'current_class', 'photo'])
        MockClass = namedtuple('MockClass', ['name'])
        mock_student = MockStudent(
            get_full_name=lambda: "JOHN DOE",
            student_id="STU001", 
            current_class=MockClass(name="BASIC 9A"),
            photo=None
        )
        
        # Mock term
        MockTerm = namedtuple('MockTerm', ['name', 'academic_year'])
        MockAcademicYear = namedtuple('MockAcademicYear', ['name'])
        mock_term = MockTerm(
            name="THIRD TERM",
            academic_year=MockAcademicYear(name="2024/2025")
        )
        
        # Mock subject results
        MockSubjectResult = namedtuple('MockSubjectResult', ['class_subject', 'class_score', 'exam_score', 'total_score', 'grade', 'position'])
        MockClassSubject = namedtuple('MockClassSubject', ['subject'])
        MockSubject = namedtuple('MockSubject', ['name'])
        
        mock_subjects = [
            ("English Language", 42, 38, 80, "A", 1),
            ("Mathematics", 45, 40, 85, "A", 2),
            ("Integrated Science", 40, 35, 75, "B", 3),
            ("Social Studies", 41, 36, 77, "B", 4),
            ("Religious & Moral Education", 44, 41, 85, "A", 5),
        ]
        
        subject_results = []
        for name, class_score, exam_score, total, grade, pos in mock_subjects:
            subject = MockSubject(name=name)
            class_subject = MockClassSubject(subject=subject)
            result = MockSubjectResult(
                class_subject=class_subject,
                class_score=class_score,
                exam_score=exam_score,
                total_score=total,
                grade=grade,
                position=pos
            )
            subject_results.append(result)
        
        # Mock term result
        MockTermResult = namedtuple('MockTermResult', ['class_position', 'average_score'])
        term_result = MockTermResult(class_position=5, average_score=80.4)
        
        # Create context
        context = {
            'school': school,
            'student': mock_student,
            'term': mock_term,
            'subject_results': subject_results,
            'term_result': term_result,
            'class_teacher_name': "MR. JOHN DOE",
            'position': "5/25",
            'reopening_date': None,
            'attendance': None,
            'behaviour': None,
            'empty_rows': range(4),  # 9 - 5 subjects
            'total_marks_ca': sum(r.class_score for r in subject_results),
            'total_marks_exam': sum(r.exam_score for r in subject_results),
            'total_marks_overall': sum(r.total_score for r in subject_results),
            'media_url_base': 'http://localhost:8000/media/',
            'is_preview': False
        }
        
        print("Generating HTML preview...")
        
        # Generate HTML content
        html_content = render_to_string('reports/terminal_report.html', context)
        
        # Save HTML for preview
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_file = f.name
        
        print(f"HTML preview saved: {html_file}")
        print("Opening HTML preview in browser...")
        
        # Open in browser for visual inspection
        webbrowser.open(f'file://{html_file}')
        
        print("\n" + "="*60)
        print("VISUAL INSPECTION CHECKLIST:")
        print("="*60)
        print("Header alignment:")
        print("  - School logos on left and right sides")
        print("  - School name and info centered")
        print("  - All elements properly aligned")
        print()
        print("Watermark positioning:")
        print("  - Watermark centered behind the scores table")
        print("  - Opacity at 0.05 (very faint)")
        print("  - Does not interfere with text readability")
        print()
        print("Table layout:")
        print("  - Scores table properly formatted")
        print("  - Borders and spacing consistent")
        print("  - Text alignment correct")
        print()
        print("Overall layout:")
        print("  - A4 page dimensions (210mm width)")
        print("  - Proper margins and padding")
        print("  - Professional appearance")
        print("="*60)
        
        # Test PDF generation if wkhtmltopdf is available
        try:
            print("\nTesting PDF generation...")
            pdf_content = generate_terminal_report_pdf(context)
            
            # Save PDF for inspection
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(pdf_content)
                pdf_file = f.name
            
            print(f"PDF generated successfully: {pdf_file}")
            print("Opening PDF for comparison...")
            
            # Open PDF
            if os.name == 'nt':  # Windows
                os.startfile(pdf_file)
            else:  # macOS/Linux
                os.system(f'open "{pdf_file}"' if sys.platform == 'darwin' else f'xdg-open "{pdf_file}"')
                
        except Exception as e:
            print("Warning: PDF generation failed: {}".format(e))
            print("   This is likely due to wkhtmltopdf not being installed.")
            print("   HTML preview should still show correct alignment.")
        
        print("\nTest completed!")
        print("   Compare the HTML preview and PDF (if generated)")
        print("   Both should have identical alignment and watermark positioning")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pdf_alignment()
    sys.exit(0 if success else 1)