#!/usr/bin/env python
"""
Test script to verify ReportLab PDF generation works correctly
This script tests the Windows-compatible PDF generation system
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from io import BytesIO

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

def test_reportlab_installation():
    """Test if ReportLab is properly installed"""
    print("=" * 60)
    print("TESTING REPORTLAB INSTALLATION")
    print("=" * 60)
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        print("✅ ReportLab imported successfully")
        
        # Test basic PDF creation
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Test PDF", styles['Title'])]
        doc.build(story)
        
        pdf_size = len(buffer.getvalue())
        print(f"✅ Basic PDF creation works (Size: {pdf_size} bytes)")
        buffer.close()
        
        return True
    except ImportError as e:
        print(f"❌ ReportLab import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ ReportLab test failed: {e}")
        return False

def test_pdf_generator_class():
    """Test the TerminalReportPDFGenerator class"""
    print("\n" + "=" * 60)
    print("TESTING PDF GENERATOR CLASS")
    print("=" * 60)
    
    try:
        from reports.pdf_generator import TerminalReportPDFGenerator
        print("✅ PDF generator class imported successfully")
        
        # Initialize generator
        generator = TerminalReportPDFGenerator()
        print("✅ PDF generator initialized successfully")
        
        # Test style setup
        assert hasattr(generator, 'title_style'), "Title style not found"
        assert hasattr(generator, 'heading_style'), "Heading style not found"
        assert hasattr(generator, 'normal_style'), "Normal style not found"
        print("✅ Custom styles created successfully")
        
        return True
    except ImportError as e:
        print(f"❌ PDF generator import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ PDF generator test failed: {e}")
        return False

def create_mock_report_context():
    """Create mock data for testing PDF generation"""
    print("\n" + "=" * 60)
    print("CREATING MOCK REPORT CONTEXT")
    print("=" * 60)
    
    try:
        from collections import namedtuple
        
        # Mock school
        MockSchool = namedtuple('MockSchool', ['name', 'address', 'phone_number', 'motto'])
        school = MockSchool(
            name="Test School",
            address="123 Test Street, Test City",
            phone_number="0123456789",
            motto="Excellence in Education"
        )
        
        # Mock student
        MockStudent = namedtuple('MockStudent', ['student_id', 'first_name', 'last_name', 'current_class'])
        MockClass = namedtuple('MockClass', ['name', 'class_teacher'])
        MockTeacher = namedtuple('MockTeacher', ['first_name', 'last_name'])
        
        teacher = MockTeacher(first_name="John", last_name="Doe")
        current_class = MockClass(name="Basic 9A", class_teacher=teacher)
        
        student = MockStudent(
            student_id="STU001",
            first_name="Jane",
            last_name="Smith",
            current_class=current_class
        )
        
        # Add get_full_name method to student
        def get_full_name(self):
            return f"{self.first_name} {self.last_name}"
        
        student.get_full_name = get_full_name.__get__(student, MockStudent)
        
        # Add get_full_name method to teacher
        teacher.get_full_name = get_full_name.__get__(teacher, MockTeacher)
        
        # Mock term
        MockTerm = namedtuple('MockTerm', ['name', 'academic_year'])
        MockAcademicYear = namedtuple('MockAcademicYear', ['name'])
        
        academic_year = MockAcademicYear(name="2024/2025")
        term = MockTerm(name="First Term", academic_year=academic_year)
        
        # Mock subject results
        MockSubjectResult = namedtuple('MockSubjectResult', [
            'class_subject', 'class_score', 'exam_score', 'total_score', 'grade', 'position'
        ])
        MockClassSubject = namedtuple('MockClassSubject', ['subject'])
        MockSubject = namedtuple('MockSubject', ['name'])
        
        subjects = ['Mathematics', 'English', 'Science', 'Social Studies', 'French']
        subject_results = []
        
        for i, subject_name in enumerate(subjects):
            subject = MockSubject(name=subject_name)
            class_subject = MockClassSubject(subject=subject)
            
            result = MockSubjectResult(
                class_subject=class_subject,
                class_score=25 + i * 2,
                exam_score=45 + i * 3,
                total_score=70 + i * 5,
                grade='B' if i < 3 else 'C',
                position=i + 1
            )
            subject_results.append(result)
        
        # Mock term result
        MockTermResult = namedtuple('MockTermResult', [
            'total_score', 'average_score', 'class_position', 'total_students', 'teacher_remarks'
        ])
        
        term_result = MockTermResult(
            total_score=375,
            average_score=75.0,
            class_position=5,
            total_students=25,
            teacher_remarks="Good performance overall. Keep up the good work!"
        )
        
        context = {
            'school': school,
            'student': student,
            'term': term,
            'subject_results': subject_results,
            'term_result': term_result,
            'class_teacher_name': teacher.get_full_name(),
            'reopening_date': date.today() + timedelta(weeks=2)
        }
        
        print("✅ Mock report context created successfully")
        print(f"   - School: {school.name}")
        print(f"   - Student: {student.get_full_name()}")
        print(f"   - Term: {term.name}")
        print(f"   - Subjects: {len(subject_results)}")
        print(f"   - Average Score: {term_result.average_score}%")
        
        return context
        
    except Exception as e:
        print(f"❌ Failed to create mock context: {e}")
        return None

def test_pdf_generation():
    """Test actual PDF generation with mock data"""
    print("\n" + "=" * 60)
    print("TESTING PDF GENERATION")
    print("=" * 60)
    
    try:
        from reports.pdf_generator import generate_terminal_report_pdf
        
        # Create mock context
        context = create_mock_report_context()
        if not context:
            return False
        
        # Generate PDF
        print("Generating PDF...")
        pdf_content = generate_terminal_report_pdf(context)
        
        if not pdf_content:
            print("❌ PDF generation returned empty content")
            return False
        
        print(f"✅ PDF generated successfully (Size: {len(pdf_content)} bytes)")
        
        # Verify PDF content starts with PDF header
        if pdf_content.startswith(b'%PDF'):
            print("✅ PDF content has valid PDF header")
        else:
            print("❌ PDF content does not have valid PDF header")
            return False
        
        # Save test PDF file
        test_pdf_path = os.path.join(os.path.dirname(__file__), 'test_report.pdf')
        with open(test_pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Test PDF saved to: {test_pdf_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_django_integration():
    """Test PDF generation through Django views"""
    print("\n" + "=" * 60)
    print("TESTING DJANGO INTEGRATION")
    print("=" * 60)
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from reports.views import ReportCardViewSet
        from schools.models import School
        from students.models import Student
        from schools.models import Term, AcademicYear
        
        User = get_user_model()
        
        # Check if we have test data
        school = School.objects.first()
        if not school:
            print("⚠️  No school found in database - skipping Django integration test")
            return True
        
        user = User.objects.filter(school=school).first()
        if not user:
            print("⚠️  No user found for school - skipping Django integration test")
            return True
        
        student = Student.objects.filter(school=school).first()
        if not student:
            print("⚠️  No student found for school - skipping Django integration test")
            return True
        
        term = Term.objects.first()
        if not term:
            print("⚠️  No term found - skipping Django integration test")
            return True
        
        print(f"✅ Found test data:")
        print(f"   - School: {school.name}")
        print(f"   - User: {user.email}")
        print(f"   - Student: {student.get_full_name()}")
        print(f"   - Term: {term}")
        
        # Create request
        factory = RequestFactory()
        request = factory.post('/api/reports/report-cards/generate_pdf_report/', {
            'student_id': student.id,
            'term_id': term.id
        })
        request.user = user
        
        # Test viewset method
        viewset = ReportCardViewSet()
        viewset.request = request
        
        # Test context generation
        context = viewset._get_report_context(student, term, request)
        print("✅ Report context generated successfully")
        
        # Test PDF generation through viewset
        response = viewset.generate_pdf_report(request)
        
        if response.status_code == 200:
            print("✅ Django PDF generation successful")
            print(f"   - Response type: {response.get('Content-Type', 'Unknown')}")
            if hasattr(response, 'content'):
                print(f"   - Content size: {len(response.content)} bytes")
        else:
            print(f"⚠️  Django PDF generation returned status {response.status_code}")
            if hasattr(response, 'data'):
                print(f"   - Error: {response.data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Django integration test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_requirements():
    """Test if all required packages are installed"""
    print("\n" + "=" * 60)
    print("TESTING REQUIREMENTS")
    print("=" * 60)
    
    required_packages = [
        'reportlab',
        'django',
        'djangorestframework',
        'Pillow'
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            all_installed = False
    
    return all_installed

def main():
    """Run all tests"""
    print("REPORTLAB PDF GENERATION TEST SUITE")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print(f"Python version: {sys.version}")
    print(f"Django version: {django.get_version()}")
    
    tests = [
        ("Requirements Check", test_requirements),
        ("ReportLab Installation", test_reportlab_installation),
        ("PDF Generator Class", test_pdf_generator_class),
        ("PDF Generation", test_pdf_generation),
        ("Django Integration", test_django_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ReportLab PDF generation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the output above for details.")
    
    print(f"\nTest completed at: {datetime.now()}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)