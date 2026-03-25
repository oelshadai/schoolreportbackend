from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import ReportCard
from django.views.decorators.clickjacking import xframe_options_exempt
from .serializers import ReportCardSerializer
from students.models import Student, Attendance, Behaviour
from scores.models import SubjectResult, TermResult
from schools.models import Term


class ReportCardViewSet(viewsets.ModelViewSet):
    """Report Card management"""
    queryset = ReportCard.objects.all()
    serializer_class = ReportCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = ReportCard.objects.filter(student__school=user.school)
            
            # Class teachers can only see reports for their class students
            if user.role == 'TEACHER':
                # Find classes where user is class teacher
                from schools.models import Class
                teacher_classes = Class.objects.filter(school=user.school, class_teacher=user)
                if teacher_classes.exists():
                    # Filter to only students in their classes
                    class_ids = teacher_classes.values_list('id', flat=True)
                    queryset = queryset.filter(student__current_class_id__in=class_ids)
                else:
                    # Teacher is not a class teacher, no access to reports
                    return ReportCard.objects.none()
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            class_id = self.request.query_params.get('class_id')
            if class_id and user.role != 'TEACHER':  # Only admins can filter by any class
                queryset = queryset.filter(student__current_class_id=class_id)
            
            status_filter = self.request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            return queryset
        return ReportCard.objects.none()
    
    def _get_report_context(self, student, term, request):
        """Get EXACT same context for both preview and PDF generation - SINGLE SOURCE OF TRUTH"""
        # Get all required data
        subject_results = SubjectResult.objects.filter(
            student=student,
            term=term
        ).select_related('class_subject__subject')
        
        term_result = TermResult.objects.filter(
            student=student,
            term=term
        ).first()
        
        attendance = Attendance.objects.filter(
            student=student,
            term=term
        ).first()
        
        behaviour = Behaviour.objects.filter(
            student=student,
            term=term
        ).first()
        
        # Get class teacher name
        class_teacher_name = ""
        if student.current_class and student.current_class.class_teacher:
            class_teacher_name = student.current_class.class_teacher.get_full_name()
        
        # Calculate reopening date
        from datetime import timedelta
        reopening_date = term.end_date + timedelta(weeks=2) if term.end_date else None
        
        # Calculate total marks for template
        total_marks_ca = sum(sr.ca_score for sr in subject_results) if subject_results else 0
        total_marks_exam = sum(sr.exam_score for sr in subject_results) if subject_results else 0
        total_marks_overall = total_marks_ca + total_marks_exam
        
        # Get media URL base for logo display
        from .utils import get_media_base_url
        media_url_base = get_media_base_url(request)
        
        return {
            'school': student.school,
            'student': student,
            'term': term,
            'term_result': term_result,
            'subject_results': subject_results,
            'class_teacher_name': class_teacher_name,
            'position': f"{term_result.class_position}/{term_result.total_students}" if (term_result and term_result.class_position) else "N/A",
            'reopening_date': reopening_date,
            'attendance': attendance,
            'behaviour': behaviour,
            'empty_rows': range(max(0, 9 - subject_results.count())),
            'total_marks_ca': total_marks_ca,
            'total_marks_exam': total_marks_exam,
            'total_marks_overall': total_marks_overall,
            'media_url_base': media_url_base,
        }
    
    def _get_sample_report_context(self, school, sample_data, request):
        """Get EXACT same context for sample data - SINGLE SOURCE OF TRUTH"""
        # Get class teacher name from actual student's class or mock
        class_teacher_name = ""
        if hasattr(sample_data['student'], 'current_class') and sample_data['student'].current_class and hasattr(sample_data['student'].current_class, 'class_teacher') and sample_data['student'].current_class.class_teacher:
            class_teacher_name = sample_data['student'].current_class.class_teacher.get_full_name()
        
        # Use actual school term dates if available
        reopening_date = None
        if hasattr(sample_data['term'], 'end_date') and sample_data['term'].end_date:
            from datetime import timedelta
            reopening_date = sample_data['term'].end_date + timedelta(weeks=2)
        elif getattr(school, 'term_reopening_date', None):
            from datetime import datetime
            reopening_date = datetime.strptime(school.term_reopening_date, '%Y-%m-%d').date()
        else:
            from datetime import datetime, timedelta
            reopening_date = datetime.now().date() + timedelta(weeks=2)
        
        # Get media URL base for logo display
        from .utils import get_media_base_url
        media_url_base = get_media_base_url(request)
        
        return {
            'school': school,
            'student': sample_data['student'],
            'student_name': sample_data['student'].get_full_name() if hasattr(sample_data['student'], 'get_full_name') else f"{sample_data['student'].first_name} {sample_data['student'].last_name}",
            'term': sample_data['term'],
            'subject_results': sample_data['subject_results'],
            'term_result': sample_data['term_result'],
            'attendance': sample_data['attendance'],
            'behaviour': sample_data['behaviour'],
            'class_teacher_name': class_teacher_name,
            'reopening_date': reopening_date,
            'position': f"{sample_data['term_result'].position}/{25}",  # Use sample class size
            'empty_rows': range(max(0, 9 - len(sample_data['subject_results']))),
            'is_preview': True,
            'media_url_base': media_url_base,
            'total_marks_ca': sum(r.ca_score for r in sample_data['subject_results']),
            'total_marks_exam': sum(r.exam_score for r in sample_data['subject_results']),
            'total_marks_overall': sum(r.total_score for r in sample_data['subject_results']),
        }

    @action(detail=False, methods=['post'])
    def generate_pdf_report(self, request):
        """Generate PDF report using the EXACT same context and template as preview"""
        student_id = request.data.get('student_id')
        term_id = request.data.get('term_id')
        
        if not student_id or not term_id:
            return Response(
                {"error": "student_id and term_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Students can only download their own report; staff can download any in their school
            if getattr(request.user, 'role', None) == 'STUDENT':
                from students.models import Student as StudentModel
                student = StudentModel.objects.get(id=student_id, user=request.user)
            else:
                student = Student.objects.get(id=student_id, school=request.user.school)
            term = Term.objects.get(id=term_id)
            
            # Get EXACT same context as preview - SINGLE SOURCE OF TRUTH
            context = self._get_report_context(student, term, request)
            
            # Generate PDF using the same HTML template as preview
            from .pdf_generator import generate_terminal_report_pdf
            from django.http import HttpResponse
            
            pdf_content = generate_terminal_report_pdf(context)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{student.student_id}_{term.name}_Report.pdf"'
            return response
            
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Term.DoesNotExist:
            return Response(
                {"error": "Term not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Generate PDF report card for a student"""
        student_id = request.data.get('student_id')
        term_id = request.data.get('term_id')
        
        if not student_id or not term_id:
            return Response(
                {"error": "student_id and term_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id, school=request.user.school)
            term = Term.objects.get(id=term_id)
            
            # Check permissions for class teachers
            if request.user.role == 'TEACHER':
                from schools.models import Class
                teacher_class = Class.objects.filter(
                    school=request.user.school, 
                    class_teacher=request.user,
                    id=student.current_class_id
                ).first()
                
                if not teacher_class:
                    return Response(
                        {"error": "You can only generate reports for students in your assigned class"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get all required data
            subject_results = SubjectResult.objects.filter(
                student=student,
                term=term
            ).select_related('class_subject__subject')
            
            if not subject_results.exists():
                return Response(
                    {"error": "No results found for this student and term"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get or create term result
            term_result = TermResult.objects.filter(
                student=student,
                term=term
            ).first()
            
            if not term_result:
                # Auto-generate term result if it doesn't exist
                if not subject_results.exists():
                    return Response(
                        {"error": "No subject results found. Please enter scores first."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Create term result from subject results
                total_scores = sum(sr.total_score for sr in subject_results)
                num_subjects = subject_results.count()
                average_score = round(total_scores / num_subjects, 2) if num_subjects > 0 else 0
                
                # Calculate position
                better_students = TermResult.objects.filter(
                    term=term,
                    class_instance=student.current_class,
                    average_score__gt=average_score
                ).count()
                class_position = better_students + 1
                
                term_result = TermResult.objects.create(
                    student=student,
                    term=term,
                    class_instance=student.current_class,
                    total_score=total_scores,
                    average_score=average_score,
                    subjects_count=num_subjects,
                    class_position=class_position,
                    total_students=student.current_class.students.count() if student.current_class else 1,
                    teacher_remarks=f"Auto-generated for PDF report - Average: {average_score}%"
                )
            
            attendance = Attendance.objects.filter(
                student=student,
                term=term
            ).first()
            
            behaviour = Behaviour.objects.filter(
                student=student,
                term=term
            ).first()
            
            # Create or get report card
            report_card, created = ReportCard.objects.get_or_create(
                student=student,
                term=term,
                defaults={'generated_by': request.user}
            )
            
            if created:
                report_card.generate_report_code()
            
            # Generate PDF from HTML template using HTML-to-PDF conversion
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            import subprocess
            import tempfile
            import os
            
            # Get class teacher name
            class_teacher_name = ""
            if student.current_class and student.current_class.class_teacher:
                class_teacher_name = student.current_class.class_teacher.get_full_name()
            
            # Calculate reopening date
            from datetime import timedelta
            reopening_date = term.end_date + timedelta(weeks=2) if term.end_date else None
            
            # Calculate total marks for template
            total_marks_ca = sum(sr.ca_score for sr in subject_results) if subject_results else 0
            total_marks_exam = sum(sr.exam_score for sr in subject_results) if subject_results else 0
            total_marks_overall = total_marks_ca + total_marks_exam
            
            # Get media URL base for logo display
            from .utils import get_media_base_url
            media_url_base = get_media_base_url(request)
            
            context = {
                'school': student.school,
                'student': student,
                'term': term,
                'term_result': term_result,
                'subject_results': subject_results,
                'class_teacher_name': class_teacher_name,
                'position': f"{term_result.class_position}/{term_result.total_students}",
                'reopening_date': reopening_date,
                'attendance': attendance,
                'behaviour': behaviour,
                'empty_rows': range(max(0, 9 - subject_results.count())),
                'total_marks_ca': total_marks_ca,
                'total_marks_exam': total_marks_exam,
                'total_marks_overall': total_marks_overall,
                'media_url_base': media_url_base,
            }
            
            # Render HTML template
            html_content = render_to_string('reports/terminal_report.html', context)
            
            # For now, return the HTML content (you can add HTML-to-PDF conversion here)
            # You can use libraries like weasyprint, wkhtmltopdf, or similar
            
            # Save HTML content temporarily (replace with actual PDF generation)
            pdf_filename = f"report_card_{student.student_id}_{term.id}.pdf"
            
            # Create or get report card
            report_card, created = ReportCard.objects.get_or_create(
                student=student,
                term=term,
                defaults={'generated_by': request.user}
            )
            
            if created:
                report_card.generate_report_code()
            
            # TODO: Implement actual HTML-to-PDF conversion here
            # For now, we'll save the HTML content
            from django.core.files.base import ContentFile
            report_card.pdf_file.save(pdf_filename, ContentFile(html_content.encode('utf-8')), save=False)
            
            report_card.status = 'GENERATED'
            report_card.generated_at = timezone.now()
            report_card.save()
            
            return Response({
                "message": "Report card generated successfully",
                "report_id": report_card.id,
                "pdf_url": request.build_absolute_uri(report_card.pdf_file.url) if report_card.pdf_file else None,
                "report_code": report_card.report_code
            }, status=status.HTTP_201_CREATED)
            
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Term.DoesNotExist:
            return Response(
                {"error": "Term not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def generate_terminal_report(self, request):
        """Generate and save terminal report (summary) for a student"""
        student_id = request.data.get('student_id')
        term_id = request.data.get('term_id')
        
        if not student_id or not term_id:
            return Response(
                {"error": "student_id and term_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id, school=request.user.school)
            term = Term.objects.get(id=term_id)
            
            # Check permissions for class teachers
            if request.user.role == 'TEACHER':
                from schools.models import Class
                teacher_class = Class.objects.filter(
                    school=request.user.school, 
                    class_teacher=request.user,
                    id=student.current_class_id
                ).first()
                
                if not teacher_class:
                    return Response(
                        {"error": "You can only generate terminal reports for students in your assigned class"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get all subject results for this student and term
            subject_results = SubjectResult.objects.filter(
                student=student,
                term=term
            ).select_related('class_subject__subject')
            
            if not subject_results.exists():
                return Response(
                    {"error": "No results found for this student and term. Please enter scores first."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get or create the term result (terminal report summary)
            term_result, created = TermResult.objects.get_or_create(
                student=student,
                term=term,
                defaults={
                    'class_instance': student.current_class,
                    'average_score': 0,
                    'total_students': student.current_class.students.count() if student.current_class else 1,
                    'class_position': 1,
                    'teacher_remarks': 'Terminal report generated',
                    'subjects_count': 0
                }
            )
            
            # Calculate overall average from subject results
            total_scores = sum(sr.total_score for sr in subject_results)
            num_subjects = subject_results.count()
            term_result.total_score = total_scores
            term_result.average_score = round(total_scores / num_subjects, 2) if num_subjects > 0 else 0
            term_result.subjects_count = num_subjects
            
            # Simple position calculation (can be enhanced later)
            better_students = TermResult.objects.filter(
                term=term,
                class_instance=student.current_class,
                average_score__gt=term_result.average_score
            ).count()
            term_result.class_position = better_students + 1
            
            term_result.save()
            
            # Prepare template context
            from django.template.loader import render_to_string
            from datetime import datetime, timedelta
            
            # Get class teacher name
            class_teacher_name = ""
            if student.current_class and student.current_class.class_teacher:
                class_teacher_name = student.current_class.class_teacher.get_full_name()
            
            # Calculate next term reopening date (example: 2 weeks after term ends)
            reopening_date = term.end_date + timedelta(weeks=2) if term.end_date else datetime.now().date()
            
            # Get attendance data
            attendance_obj = None
            try:
                attendance_obj = Attendance.objects.get(student=student, term=term)
            except Attendance.DoesNotExist:
                pass
            
            # Prepare empty rows for consistent table display (9 subjects max)
            empty_rows_count = max(0, 9 - num_subjects)
            empty_rows = range(empty_rows_count)
            
            # Calculate total marks for template
            total_marks_ca = sum(sr.ca_score for sr in subject_results) if subject_results else 0
            total_marks_exam = sum(sr.exam_score for sr in subject_results) if subject_results else 0
            total_marks_overall = total_marks_ca + total_marks_exam
            
            context = {
                'school': student.school,
                'student': student,
                'term': term,
                'term_result': term_result,
                'subject_results': subject_results,
                'class_teacher_name': class_teacher_name,
                'position': f"{term_result.class_position}/{term_result.total_students}",
                'reopening_date': reopening_date,
                'attendance': attendance_obj,
                'empty_rows': empty_rows,
                'total_marks_ca': total_marks_ca,
                'total_marks_exam': total_marks_exam,
                'total_marks_overall': total_marks_overall,
            }
            
            # Render HTML template
            html_content = render_to_string('reports/terminal_report.html', context)
            
            return Response({
                "success": True,
                "message": f"Terminal report generated successfully for {student.get_full_name()}",
                "term_result_id": term_result.id,
                "average_score": term_result.average_score,
                "total_score": term_result.total_score,
                "position": f"{term_result.class_position}/{term_result.total_students}",
                "subjects_count": num_subjects,
                "html_content": html_content,
                "template_url": f"/api/reports/terminal-report-preview/{term_result.id}/"
            }, status=status.HTTP_201_CREATED)
            
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Term.DoesNotExist:
            return Response(
                {"error": "Term not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate terminal report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def preview_terminal_report(self, request):
        """Preview terminal report with current scores (before saving)"""
        student_id = request.data.get('student_id')
        term_id = request.data.get('term_id')
        preview_scores = request.data.get('preview_scores', {})
        
        if not student_id or not term_id:
            return Response(
                {"error": "student_id and term_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id, school=request.user.school)
            term = Term.objects.get(id=term_id)
            
            # Check permissions for class teachers
            if request.user.role == 'TEACHER':
                from schools.models import Class
                teacher_class = Class.objects.filter(
                    school=request.user.school, 
                    class_teacher=request.user,
                    id=student.current_class_id
                ).first()
                
                if not teacher_class:
                    return Response(
                        {"error": "You can only preview reports for students in your assigned class"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Create mock subject results from preview scores
            from collections import namedtuple
            from schools.models import ClassSubject, Subject
            
            MockSubjectResult = namedtuple('MockSubjectResult', [
                'class_subject', 'task', 'homework', 'group_work', 'project_work', 
                'class_test', 'exam_score', 'total_score', 'ca_score', 'grade', 'position'
            ])
            
            MockClassSubject = namedtuple('MockClassSubject', ['subject'])
            MockSubject = namedtuple('MockSubject', ['name'])
            
            mock_subject_results = []
            total_scores_sum = 0
            subject_count = 0
            
            for class_subject_id, score_data in preview_scores.items():
                try:
                    class_subject = ClassSubject.objects.get(id=class_subject_id)
                    
                    # Calculate scores
                    class_score = float(score_data.get('task', 0)) + float(score_data.get('homework', 0)) + \
                                 float(score_data.get('group_work', 0)) + float(score_data.get('project_work', 0)) + \
                                 float(score_data.get('class_test', 0))
                    exam_score = float(score_data.get('exam_score', 0))
                    total_score = class_score + exam_score
                    
                    # Simple grade calculation
                    if total_score >= 80:
                        grade = 'A'
                    elif total_score >= 70:
                        grade = 'B'
                    elif total_score >= 60:
                        grade = 'C'
                    elif total_score >= 50:
                        grade = 'D'
                    else:
                        grade = 'F'
                    
                    mock_result = MockSubjectResult(
                        class_subject=class_subject,
                        task=score_data.get('task', 0),
                        homework=score_data.get('homework', 0),
                        group_work=score_data.get('group_work', 0),
                        project_work=score_data.get('project_work', 0),
                        class_test=score_data.get('class_test', 0),
                        exam_score=exam_score,
                        total_score=total_score,
                        ca_score=class_score,
                        grade=grade,
                        position=1  # Default for preview
                    )
                    
                    mock_subject_results.append(mock_result)
                    total_scores_sum += total_score
                    subject_count += 1
                    
                except ClassSubject.DoesNotExist:
                    continue
            
            # Create mock term result
            MockTermResult = namedtuple('MockTermResult', [
                'average_score', 'total_score', 'class_position', 'total_students', 
                'teacher_remarks', 'promoted'
            ])
            
            average_score = round(total_scores_sum / subject_count, 2) if subject_count > 0 else 0
            mock_term_result = MockTermResult(
                average_score=average_score,
                total_score=total_scores_sum,
                class_position=1,
                total_students=student.current_class.students.count() if student.current_class else 1,
                teacher_remarks=f"Preview report - Average: {average_score}%",
                promoted=average_score >= 50
            )
            
            # Store preview data in Django cache for the preview endpoint (expires in 5 minutes)
            from django.core.cache import cache
            preview_id = f"preview_{student_id}_{term_id}_{request.user.id}"
            cache.set(preview_id, {
                'student_id': student_id,
                'term_id': term_id,
                'user_id': request.user.id,
                'school_id': request.user.school.id,
                'subject_results': [
                    {
                        'subject_name': result.class_subject.subject.name,
                        'ca_score': result.ca_score,
                        'exam_score': result.exam_score,
                        'total_score': result.total_score,
                        'grade': result.grade,
                        'position': result.position
                    }
                    for result in mock_subject_results
                ],
                'term_result': {
                    'average_score': mock_term_result.average_score,
                    'total_score': mock_term_result.total_score,
                    'class_position': mock_term_result.class_position,
                    'total_students': mock_term_result.total_students,
                    'teacher_remarks': mock_term_result.teacher_remarks,
                    'promoted': mock_term_result.promoted
                }
            }, timeout=300)  # 5 minutes
            
            return Response({
                "success": True,
                "message": f"Preview generated for {student.get_full_name()}",
                "preview_url": f"/api/reports/report-cards/preview-terminal-report/{preview_id}/",
                "average_score": average_score,
                "subjects_count": subject_count
            }, status=status.HTTP_200_OK)
            
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Term.DoesNotExist:
            return Response(
                {"error": "Term not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='preview-terminal-report/(?P<preview_id>[^/.]+)', 
            authentication_classes=[], permission_classes=[])  # Bypass DRF authentication for custom handling
    def preview_terminal_report_view(self, request, preview_id=None):
        """View preview terminal report from cache data"""
        from django.views.decorators.clickjacking import xframe_options_exempt
        
        # Apply the xframe_options_exempt decorator to the response
        response = self._generate_preview_response(request, preview_id)
        # Remove X-Frame-Options to allow iframe embedding from frontend
        return response
    
    def _generate_preview_response(self, request, preview_id):
        """Generate the actual preview response"""
        try:
            # Handle JWT token authentication from URL parameter
            token_param = request.GET.get('token')
            if not token_param:
                response = HttpResponse(
                    "<h1>Authentication Required</h1><p>No authentication token provided.</p>",
                    status=401
                )
                # Remove X-Frame-Options to allow iframe embedding from frontend
                return response
            
            from rest_framework_simplejwt.authentication import JWTAuthentication
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
            
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token_param)
                user = jwt_auth.get_user(validated_token)
                # Manually set the user for this request
                request.user = user
                # Authentication successful for user
            except (InvalidToken, TokenError) as e:
                # Token authentication failed
                response = HttpResponse(
                    "<h1>Authentication Failed</h1><p>Invalid or expired token.</p>",
                    status=401
                )
                # Remove X-Frame-Options to allow iframe embedding from frontend
                return response
            
            from django.template.loader import render_to_string
            from datetime import datetime, timedelta
            from collections import namedtuple
            from django.http import HttpResponse
            from django.http import HttpResponse
            
            # Preview request for ID
            
            # Get preview data from cache instead of session
            from django.core.cache import cache
            preview_data = cache.get(preview_id)
            if not preview_data:
                # No preview data found in cache for ID
                return HttpResponse(
                    "<h1>Preview Not Found</h1><p>Preview data not found or expired. Please generate a new preview.</p>",
                    status=404
                )
            
            # Found preview data
            
            # Verify user has access to this preview
            if not request.user.is_authenticated or request.user.id != preview_data.get('user_id'):
                return HttpResponse(
                    "<h1>Access Denied</h1><p>You don't have permission to view this preview.</p>",
                    status=403
                )
            
            student = Student.objects.get(id=preview_data['student_id'], school_id=preview_data['school_id'])
            term = Term.objects.get(id=preview_data['term_id'])
            
            # Student and Term info
            
            # Create mock objects from session data
            MockSubjectResult = namedtuple('MockSubjectResult', [
                'class_subject', 'ca_score', 'exam_score', 'total_score', 'grade', 'position'
            ])
            MockClassSubject = namedtuple('MockClassSubject', ['subject'])
            MockSubject = namedtuple('MockSubject', ['name'])
            MockTermResult = namedtuple('MockTermResult', [
                'average_score', 'total_score', 'class_position', 'total_students', 
                'teacher_remarks', 'promoted'
            ])
            
            # Reconstruct subject results
            subject_results = []
            for result_data in preview_data['subject_results']:
                mock_subject = MockSubject(name=result_data['subject_name'])
                mock_class_subject = MockClassSubject(subject=mock_subject)
                mock_result = MockSubjectResult(
                    class_subject=mock_class_subject,
                    ca_score=result_data['ca_score'],
                    exam_score=result_data['exam_score'],
                    total_score=result_data['total_score'],
                    grade=result_data['grade'],
                    position=result_data['position']
                )
                subject_results.append(mock_result)
            
            # Created mock subject results
            
            # Reconstruct term result
            term_result_data = preview_data['term_result']
            term_result = MockTermResult(
                average_score=term_result_data['average_score'],
                total_score=term_result_data['total_score'],
                class_position=term_result_data['class_position'],
                total_students=term_result_data['total_students'],
                teacher_remarks=term_result_data['teacher_remarks'],
                promoted=term_result_data['promoted']
            )
            
            # Get class teacher name
            class_teacher_name = ""
            if student.current_class and student.current_class.class_teacher:
                class_teacher_name = student.current_class.class_teacher.get_full_name()
            
            # Calculate next term reopening date
            reopening_date = term.end_date + timedelta(weeks=2) if term.end_date else datetime.now().date()
            
            # Get attendance data
            attendance_obj = None
            try:
                attendance_obj = Attendance.objects.get(student=student, term=term)
            except Attendance.DoesNotExist:
                pass
            
            # Prepare empty rows for table
            empty_rows_count = max(0, 9 - len(subject_results))
            empty_rows = range(empty_rows_count)
            
            context = {
                'school': student.school,
                'student': student,
                'term': term,
                'term_result': term_result,
                'subject_results': subject_results,
                'class_teacher_name': class_teacher_name,
                'position': f"{term_result.class_position}/{term_result.total_students}",
                'reopening_date': reopening_date,
                'attendance': attendance_obj,
                'empty_rows': empty_rows,
                'is_preview': True,  # Flag to indicate this is a preview
            }
            
            # Rendering template with context
            
            # Render HTML template
            from django.shortcuts import render
            response = render(request, 'reports/terminal_report.html', context)
            # Remove X-Frame-Options to allow iframe embedding from frontend
            return response
            
        except Exception as e:
            # Preview error
            import traceback
            response = HttpResponse(
                f"<h1>Preview Error</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>",
                status=500
            )
            # Remove X-Frame-Options to allow iframe embedding from frontend
            return response

    @action(detail=False, methods=['get'], url_path='terminal-report-preview/(?P<term_result_id>[^/.]+)')
    def terminal_report_preview(self, request, term_result_id=None):
        """Preview terminal report as HTML using SAME template as PDF"""
        try:
            term_result = TermResult.objects.get(id=term_result_id)
            student = term_result.student
            term = term_result.term
            
            # Check permissions
            if request.user.role == 'TEACHER':
                from schools.models import Class
                teacher_class = Class.objects.filter(
                    school=request.user.school, 
                    class_teacher=request.user,
                    id=student.current_class_id
                ).first()
                
                if not teacher_class:
                    return Response(
                        {"error": "You can only preview terminal reports for students in your assigned class"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Use SAME context as PDF generation
            context = self._get_report_context(student, term, request)
            
            # Render SAME template as PDF
            from django.shortcuts import render
            return render(request, 'reports/terminal_report.html', context)
            
        except TermResult.DoesNotExist:
            return Response(
                {"error": "Terminal report not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to preview terminal report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate reports for multiple students"""
        term_id = request.data.get('term_id')
        class_id = request.data.get('class_id')
        
        if not term_id:
            return Response(
                {"error": "term_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            term = Term.objects.get(id=term_id)
            students = Student.objects.filter(school=request.user.school, is_active=True)
            
            # Handle permissions for class teachers
            if request.user.role == 'TEACHER':
                from schools.models import Class
                teacher_classes = Class.objects.filter(
                    school=request.user.school, 
                    class_teacher=request.user
                )
                
                if not teacher_classes.exists():
                    return Response(
                        {"error": "You are not assigned as a class teacher"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Filter to only their class students
                teacher_class_ids = teacher_classes.values_list('id', flat=True)
                students = students.filter(current_class_id__in=teacher_class_ids)
                
                # If class_id is provided, ensure it's their class
                if class_id and int(class_id) not in teacher_class_ids:
                    return Response(
                        {"error": "You can only generate reports for your assigned class"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            if class_id:
                students = students.filter(current_class_id=class_id)
            
            generated_count = 0
            errors = []
            
            for student in students:
                try:
                    # Generate HTML report for each student
                    from django.template.loader import render_to_string
                    from datetime import timedelta
                    
                    # Get class teacher name
                    class_teacher_name = ""
                    if student.current_class and student.current_class.class_teacher:
                        class_teacher_name = student.current_class.class_teacher.get_full_name()
                    
                    # Calculate reopening date
                    reopening_date = term.end_date + timedelta(weeks=2) if term.end_date else None
                    
                    # Calculate total marks
                    total_marks_ca = sum(sr.ca_score for sr in subject_results) if subject_results else 0
                    total_marks_exam = sum(sr.exam_score for sr in subject_results) if subject_results else 0
                    total_marks_overall = total_marks_ca + total_marks_exam
                    
                    # Get media URL base
                    from .utils import get_media_base_url
                    media_url_base = get_media_base_url(request)
                    
                    context = {
                        'school': student.school,
                        'student': student,
                        'term': term,
                        'term_result': term_result,
                        'subject_results': subject_results,
                        'class_teacher_name': class_teacher_name,
                        'position': f"{term_result.class_position}/{term_result.total_students}",
                        'reopening_date': reopening_date,
                        'attendance': attendance,
                        'behaviour': behaviour,
                        'empty_rows': range(max(0, 9 - subject_results.count())),
                        'total_marks_ca': total_marks_ca,
                        'total_marks_exam': total_marks_exam,
                        'total_marks_overall': total_marks_overall,
                        'media_url_base': media_url_base,
                    }
                    
                    html_content = render_to_string('reports/terminal_report.html', context)
                    
                    report_card, created = ReportCard.objects.get_or_create(
                        student=student,
                        term=term,
                        defaults={'generated_by': request.user}
                    )
                    
                    if created:
                        report_card.generate_report_code()
                    
                    pdf_filename = f"report_card_{student.student_id}_{term.id}.pdf"
                    
                    # TODO: Replace with actual HTML-to-PDF conversion
                    from django.core.files.base import ContentFile
                    report_card.pdf_file.save(pdf_filename, ContentFile(html_content.encode('utf-8')), save=False)
                    
                    report_card.status = 'GENERATED'
                    report_card.generated_at = timezone.now()
                    report_card.save()
                    
                    generated_count += 1
                    
                except Exception as e:
                    errors.append(f"{student.get_full_name()}: {str(e)}")
            
            return Response({
                "message": f"Generated {generated_count} report cards",
                "errors": errors
            })
            
        except Term.DoesNotExist:
            return Response(
                {"error": "Term not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Bulk generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def publish_bulk(self, request):
        """Publish multiple report cards at once"""
        from .publish_bulk import _publish_bulk_impl
        return _publish_bulk_impl(self, request)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a report card"""
        report_card = self.get_object()
        
        if report_card.status != 'GENERATED':
            return Response(
                {"error": "Report must be generated before publishing"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report_card.status = 'PUBLISHED'
        report_card.published_at = timezone.now()
        report_card.save()
        
        return Response({"message": "Report card published successfully"})
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a report card (retract from student view)"""
        report_card = self.get_object()
        
        if report_card.status != 'PUBLISHED':
            return Response(
                {"error": "Report must be published to unpublish"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Revert to GENERATED status so it can be re-published later
        report_card.status = 'GENERATED'  
        report_card.published_at = None
        report_card.save()
        
        return Response({
            "message": "Report unpublished successfully - students can no longer view it",
            "report_card": ReportCardSerializer(report_card).data
        })
    
    @action(detail=False, methods=['get'])
    def published_reports(self, request):
        """Get list of published reports for teacher's class"""
        user = request.user
        term_id = request.query_params.get('term_id')
        
        if user.role != 'TEACHER':
            return Response(
                {"error": "Only teachers can view published reports"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Find teacher's classes
        from schools.models import Class
        teacher_classes = Class.objects.filter(school=user.school, class_teacher=user)
        
        if not teacher_classes.exists():
            return Response([])
        
        # Get published reports for teacher's class students
        class_ids = teacher_classes.values_list('id', flat=True)
        queryset = ReportCard.objects.filter(
            student__current_class_id__in=class_ids,
            status='PUBLISHED'
        )
        
        if term_id:
            queryset = queryset.filter(term_id=term_id)
            
        # Select related to reduce database queries
        queryset = queryset.select_related('student', 'term').order_by('-published_at')
        
        # Format the response data
        published_reports = []
        for report in queryset:
            published_reports.append({
                'id': report.id,
                'student_name': report.student.get_full_name(),
                'student_id': report.student.student_id,
                'report_code': report.report_code,
                'published_at': report.published_at,
                'term_name': report.term.name if report.term else 'Unknown Term'
            })
        
        return Response(published_reports)
    
    @action(detail=False, methods=['get'])
    def verify(self, request):
        """Verify a report card by code"""
        report_code = request.query_params.get('code')
        
        if not report_code:
            return Response(
                {"error": "Report code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            report_card = ReportCard.objects.get(report_code=report_code)
            serializer = self.get_serializer(report_card)
            return Response({
                "valid": True,
                "report": serializer.data
            })
        except ReportCard.DoesNotExist:
            return Response({
                "valid": False,
                "message": "Invalid report code"
            })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def template_preview(self, request):
        """Generate a sample HTML preview of the report template or PDF with ?format=pdf"""
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        from django.contrib.auth.models import User
        from students.models import Student, Class
        from schools.models import Subject
        from scores.models import SubjectResult
        import random
        
        try:
            # Handle token authentication from query params for direct browser access
            if not request.user.is_authenticated:
                token_param = request.GET.get('token')
                if token_param:
                    from rest_framework_simplejwt.authentication import JWTAuthentication
                    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                    
                    try:
                        jwt_auth = JWTAuthentication()
                        validated_token = jwt_auth.get_validated_token(token_param)
                        user = jwt_auth.get_user(validated_token)
                        request.user = user
                    except (InvalidToken, TokenError):
                        return Response(
                            {"error": "Invalid token"},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                else:
                    return Response(
                        {"error": "Authentication required"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            school = request.user.school
            if not school:
                return Response(
                    {"error": "User must be associated with a school"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create sample data for preview
            sample_data = self._create_sample_report_data(school)
            
            # Generate HTML preview with proper context including actual dates
            # Get class teacher name from actual student's class or mock
            class_teacher_name = ""
            if hasattr(sample_data['student'], 'current_class') and sample_data['student'].current_class and hasattr(sample_data['student'].current_class, 'class_teacher') and sample_data['student'].current_class.class_teacher:
                class_teacher_name = sample_data['student'].current_class.class_teacher.get_full_name()
            
            # Use actual school term dates if available
            reopening_date = None
            if hasattr(sample_data['term'], 'end_date') and sample_data['term'].end_date:
                from datetime import timedelta
                reopening_date = sample_data['term'].end_date + timedelta(weeks=2)
            elif getattr(school, 'term_reopening_date', None):
                from datetime import datetime
                reopening_date = datetime.strptime(school.term_reopening_date, '%Y-%m-%d').date()
            else:
                from datetime import datetime, timedelta
                reopening_date = datetime.now().date() + timedelta(weeks=2)
            
            # Get media URL base for logo display
            from .utils import get_media_base_url
            media_url_base = get_media_base_url(request)
            
            html_context = {
                'school': school,
                'student': sample_data['student'],
                'student_name': sample_data['student'].get_full_name() if hasattr(sample_data['student'], 'get_full_name') else f"{sample_data['student'].first_name} {sample_data['student'].last_name}",
                'term': sample_data['term'],
                'subject_results': sample_data['subject_results'],
                'term_result': sample_data['term_result'],
                'attendance': sample_data['attendance'],
                'behaviour': sample_data['behaviour'],
                'class_teacher_name': class_teacher_name,
                'reopening_date': reopening_date,
                'position': f"{sample_data['term_result'].position}/{25}",  # Use sample class size
                'empty_rows': range(max(0, 9 - len(sample_data['subject_results']))),
                'is_preview': True,
                'media_url_base': media_url_base,
                'total_marks_ca': sum(r.ca_score for r in sample_data['subject_results']),
                'total_marks_exam': sum(r.exam_score for r in sample_data['subject_results']),
                'total_marks_overall': sum(r.total_score for r in sample_data['subject_results']),
            }

            if request.GET.get('format') == 'pdf':
                # Return HTML content for PDF conversion
                from django.template.loader import render_to_string
                html_content = render_to_string('reports/terminal_report.html', html_context)
                response = HttpResponse(html_content, content_type='text/html')
                response['Content-Disposition'] = 'inline; filename="template_preview.html"'
                return response
            else:
                # Return HTML preview
                from django.template.loader import render_to_string
                html_content = render_to_string('reports/terminal_report.html', html_context)
                return HttpResponse(html_content, content_type='text/html')
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def preview_data(self, request):
        """Get preview data for frontend rendering"""
        try:
            school = request.user.school
            if not school:
                return Response(
                    {"error": "User must be associated with a school"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Preview data request for school
            
            # Create sample data for preview
            sample_data = self._create_sample_report_data(school)
            
            # Sample data created successfully
            
            # Convert namedtuples to dictionaries for JSON serialization
            response_data = {
                'school': {
                    'name': getattr(school, 'name', 'Sample School'),
                    'address': getattr(school, 'address', 'Sample Address'),
                    'phone_number': getattr(school, 'phone_number', '0123456789'),
                    'motto': getattr(school, 'motto', 'Excellence in Education'),
                    'current_academic_year': getattr(school, 'current_academic_year', '2024/2025'),
                    'report_template': getattr(school, 'report_template', 'standard'),
                    'show_position_in_class': getattr(school, 'show_position_in_class', True),
                    'show_student_photos': getattr(school, 'show_student_photos', True),
                    'class_teacher_signature_required': getattr(school, 'class_teacher_signature_required', False),
                    'show_headteacher_signature': getattr(school, 'show_headteacher_signature', True),
                    'grade_scale_a_min': getattr(school, 'grade_scale_a_min', 80),
                    'grade_scale_b_min': getattr(school, 'grade_scale_b_min', 70),
                    'grade_scale_c_min': getattr(school, 'grade_scale_c_min', 60),
                    'grade_scale_d_min': getattr(school, 'grade_scale_d_min', 50),
                    'grade_scale_f_min': getattr(school, 'grade_scale_f_min', 0),
                },
                'student': {
                    'student_id': sample_data['student'].student_id,
                    'first_name': sample_data['student'].first_name,
                    'last_name': sample_data['student'].last_name,
                    'date_of_birth': sample_data['student'].date_of_birth,
                },
                'term': {
                    'name': sample_data['term'].name,
                    'academic_year': sample_data['term'].academic_year.name,
                },
                'subject_results': [
                    {
                        'subject_name': result.class_subject.subject.name,
                        'ca_score': result.ca_score,
                        'exam_score': result.exam_score,
                        'total_score': result.total_score,
                        'grade': result.grade,
                        'position': result.position,
                    } for result in sample_data['subject_results']
                ],
                'term_result': {
                    'total_score': sample_data['term_result'].total_score,
                    'average': sample_data['term_result'].average,
                    'position': sample_data['term_result'].position,
                    'grade': sample_data['term_result'].grade,
                    'status': sample_data['term_result'].status,
                },
                'attendance': {
                    'days_present': sample_data['attendance'].days_present,
                    'days_absent': sample_data['attendance'].days_absent,
                    'total_days': sample_data['attendance'].total_days,
                },
                'behaviour': {
                    'conduct': sample_data['behaviour'].conduct,
                    'interest': sample_data['behaviour'].interest,
                    'class_teacher_remarks': sample_data['behaviour'].class_teacher_remarks,
                }
            }
            
            # Response data prepared successfully
            return Response(response_data)
            
        except Exception as e:
            # Preview data error
            import traceback
            return Response(
                {"error": f"Failed to generate preview data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_sample_report_data(self, school):
        """Create sample data for template preview using actual school configuration"""
        try:
            from collections import namedtuple
            from schools.models import ClassSubject, AcademicYear, Term
            from students.models import Student
            import random
            
            # Creating sample data for school
            
            # Get actual student or create realistic sample
            actual_student = Student.objects.filter(school=school, is_active=True).first()
            
            class SampleStudent:
                def __init__(self, school, actual_student=None):
                    if actual_student:
                        self.student_id = actual_student.student_id
                        self.first_name = actual_student.first_name
                        self.last_name = actual_student.last_name
                        self.date_of_birth = actual_student.date_of_birth
                        self.photo = actual_student.photo if getattr(school, 'show_student_photos', True) else None
                        self.current_class = actual_student.current_class
                        self.current_class_id = actual_student.current_class_id
                    else:
                        # Fallback to sample data if no students exist
                        self.student_id = "STU001"
                        self.first_name = "John"
                        self.last_name = "Doe" 
                        self.date_of_birth = "2010-01-15"
                        self.photo = None
                        self.current_class_id = 1
                        
                        # Create mock class
                        class MockClass:
                            def __init__(self):
                                self.name = "Basic 9 A"
                                self.id = 1
                                self.level = "BASIC_9"
                                if getattr(school, 'class_teacher_signature_required', False):
                                    class MockTeacher:
                                        def get_full_name(self):
                                            return "Mr. John Doe"
                                    self.class_teacher = MockTeacher()
                                else:
                                    self.class_teacher = None
                                
                            class Students:
                                def count(self):
                                    return 25
                            
                            students = Students()
                        self.current_class = MockClass()
                    
                    self.school = school
                
                def get_full_name(self):
                    return f"{self.first_name} {self.last_name}"
            
            sample_student = SampleStudent(school, actual_student)
            # Sample student created
            
            # Get actual academic year and term or create sample
            current_academic_year = AcademicYear.objects.filter(school=school, is_current=True).first()
            current_term = None
            
            if current_academic_year:
                current_term = Term.objects.filter(academic_year=current_academic_year, is_current=True).first()
            
            class SampleTerm:
                def __init__(self, actual_term=None, school=None):
                    if actual_term:
                        self.name = actual_term.get_name_display()
                        self.id = actual_term.id
                        self.start_date = actual_term.start_date
                        self.end_date = actual_term.end_date
                        self.academic_year = actual_term.academic_year
                    else:
                        # Use school's current academic year or fallback
                        self.name = "First Term"
                        self.id = 1
                        self.start_date = None
                        self.end_date = None
                        
                        class MockAcademicYear:
                            def __init__(self, school):
                                self.name = getattr(school, 'current_academic_year', '2024/2025')
                                self.id = 1
                        
                        self.academic_year = MockAcademicYear(school)
            
            sample_term = SampleTerm(current_term, school)
            # Sample term created
            
            # Get actual subjects from school's class subjects
            actual_subjects = []
            try:
                class_subjects = ClassSubject.objects.filter(
                    class_instance__school=school
                ).select_related('subject').distinct('subject')[:9]
                
                if class_subjects.exists():
                    actual_subjects = [cs.subject.name for cs in class_subjects]
                    # Using actual school subjects
                else:
                    # No class subjects found, using defaults
                    pass
            except Exception as e:
                # Error getting school subjects
                pass
            
            # Fallback to default subjects if no actual subjects found
            if not actual_subjects:
                actual_subjects = ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Religious & Moral Education', 'French', 'Ghanaian Language']
            
            # Sample subject results using actual subjects
            SampleSubjectResult = namedtuple('SampleSubjectResult', ['class_subject', 'ca_score', 'exam_score', 'total_score', 'grade', 'position'])
            
            # Create mock class subject structure to match template expectations
            MockSubject = namedtuple('MockSubject', ['name'])
            MockClassSubject = namedtuple('MockClassSubject', ['subject'])
            
            sample_results = []
            for i, subject in enumerate(actual_subjects):
                class_score = random.randint(20, 30)
                exam_score = random.randint(25, 50)
                total = class_score + exam_score
                
                # Use actual school grade scales
                grade_scale_a_min = getattr(school, 'grade_scale_a_min', 80)
                grade_scale_b_min = getattr(school, 'grade_scale_b_min', 70)
                grade_scale_c_min = getattr(school, 'grade_scale_c_min', 60)
                grade_scale_d_min = getattr(school, 'grade_scale_d_min', 50)
                
                if total >= grade_scale_a_min:
                    grade = 'A'
                elif total >= grade_scale_b_min:
                    grade = 'B'
                elif total >= grade_scale_c_min:
                    grade = 'C'
                elif total >= grade_scale_d_min:
                    grade = 'D'
                else:
                    grade = 'F'
                
                # Create mock objects that match template structure
                mock_subject = MockSubject(name=subject)
                mock_class_subject = MockClassSubject(subject=mock_subject)
                
                sample_results.append(SampleSubjectResult(
                    class_subject=mock_class_subject,
                    ca_score=class_score,
                    exam_score=exam_score,
                    total_score=total,
                    grade=grade,
                    position=i + 1
                ))
            
            # Created sample subject results
            
            # Sample term result
            SampleTermResult = namedtuple('SampleTermResult', ['total_score', 'average', 'position', 'grade', 'status'])
            total_scores = sum(result.total_score for result in sample_results)
            average = total_scores / len(sample_results) if sample_results else 0
            
            grade_scale_b_min = getattr(school, 'grade_scale_b_min', 70)
            grade_scale_d_min = getattr(school, 'grade_scale_d_min', 50)
            
            sample_term_result = SampleTermResult(
                total_score=total_scores,
                average=round(average, 2),
                position=5,
                grade='B' if average >= grade_scale_b_min else 'C',
                status='PROMOTED' if average >= grade_scale_d_min else 'REPEAT'
            )
            
            # Sample term result created
            
            # Sample attendance - use actual school settings
            SampleAttendance = namedtuple('SampleAttendance', ['days_present', 'days_absent', 'total_days'])
            sample_attendance = None
            if getattr(school, 'show_attendance', True):
                sample_attendance = SampleAttendance(
                    days_present=85,
                    days_absent=5,
                    total_days=90
                )
            
            # Sample behaviour - use actual school settings
            SampleBehaviour = namedtuple('SampleBehaviour', ['conduct', 'attitude', 'interest', 'class_teacher_remarks'])
            sample_behaviour = None
            if getattr(school, 'show_behavior_comments', True):
                sample_behaviour = SampleBehaviour(
                    conduct='Good',
                    attitude='Excellent', 
                    interest='Very Good',
                    class_teacher_remarks='Student shows excellent potential and good behavior in class.'
                )
            
            # Sample data creation completed successfully
            
            return {
                'student': sample_student,
                'term': sample_term,
                'subject_results': sample_results,
                'term_result': sample_term_result,
                'attendance': sample_attendance,
                'behaviour': sample_behaviour
            }
            
        except Exception as e:
            # Error in _create_sample_report_data
            import traceback
            raise e


from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render
from django.http import HttpResponse

@xframe_options_exempt
def report_preview_iframe(request):
    """Secure iframe endpoint for report template preview"""
    try:
        # Check if user is authenticated through session/JWT
        if not request.user.is_authenticated:
                return HttpResponse(
                    '<div style="padding: 20px; text-align: center; font-family: Arial;">'
                    '<h3>Authentication Required</h3>'
                    '<p>Please <a href="/login" target="_parent">log in</a> to preview report templates.</p>'
                    '</div>',
                    status=200
                )
        
        school = getattr(request.user, 'school', None)
        if not school:
            return HttpResponse(
                '<div style="padding: 20px; text-align: center; font-family: Arial;">'
                '<h3>School Not Found</h3>'
                '<p>User must be associated with a school to preview reports.</p>'
                '</div>',
                status=400
            )
        
        # Reuse the existing sample data generation
        temp_vs = ReportCardViewSet()
        sample_data = temp_vs._create_sample_report_data(school)
        
        # Get media URL base for logo display
        from .utils import get_media_base_url
        media_url_base = get_media_base_url(request)
        
        context = {
            'school': school,
            'student': sample_data['student'],
            'term': sample_data['term'],
            'subject_results': sample_data['subject_results'],
            'term_result': sample_data['term_result'],
            'attendance': sample_data['attendance'],
            'behaviour': sample_data['behaviour'],
            'is_preview': True,
            'media_url_base': media_url_base
        }
        
        return render(request, 'reports/terminal_report.html', context)
        
    except Exception as e:
        return HttpResponse(
            f'<div style="padding: 20px; text-align: center; font-family: Arial;">'
            f'<h3>Preview Error</h3>'
            f'<p>Error generating preview: {str(e)}</p>'
            f'</div>',
            status=500
        )


@xframe_options_exempt
def template_preview_public(request):
    """Public template preview that accepts JWT via ?token=... and renders the template.

    This view authenticates a simplejwt token provided in the `token` query param
    and then reuses the viewset's sample-data helper to render the same template
    the admin sees (so logos and toggles match).
    """
    try:
        # If user is not authenticated, try to authenticate via JWT token in query param
        if not request.user.is_authenticated:
            token_param = request.GET.get('token')
            if token_param:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

                try:
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(token_param)
                    user = jwt_auth.get_user(validated_token)
                    request.user = user
                except (InvalidToken, TokenError):
                    return HttpResponse(
                        '<div style="padding:20px; text-align:center;">Invalid token provided. Please <a href="/login" target="_parent">log in</a> again.</div>',
                        status=200
                    )
            else:
                return HttpResponse(
                    '<div style="padding:20px; text-align:center;">Authentication required. Please <a href="/login" target="_parent">log in</a>.</div>',
                    status=200
                )

        school = getattr(request.user, 'school', None)
        if not school:
            return HttpResponse(
                '<div style="padding:20px; text-align:center;">User must be associated with a school to preview reports.</div>',
                status=400
            )

        # Check if this is a student-specific preview with current scores
        student_id = request.GET.get('student_id')
        term_id = request.GET.get('term_id')
        current_scores_param = request.GET.get('current_scores')
        
        if student_id and term_id and current_scores_param:
            # This is a student-specific preview with current scores
            try:
                import json
                from urllib.parse import unquote
                from collections import namedtuple
                from schools.models import ClassSubject, Term
                from students.models import Student, Attendance, Behaviour
                
                # Parse the current scores (may be empty if user cleared them)
                current_scores = json.loads(unquote(current_scores_param))
                
                # Get the actual student and term
                student = Student.objects.get(id=student_id, school=school)
                term = Term.objects.get(id=term_id)
                
                # If current_scores is empty, load from database instead
                if not current_scores:
                    from scores.models import SubjectResult
                    db_results = SubjectResult.objects.filter(
                        student=student, term=term
                    ).select_related('class_subject__subject')
                    
                    if not db_results.exists():
                        return HttpResponse(
                            '<div style="padding:20px; text-align:center; font-family:Arial,sans-serif;"'
                            '><h3>No Scores Available</h3>'
                            '<p>No scores have been entered for this student yet.</p></div>',
                            status=200
                        )
                    
                    for sr in db_results:
                        current_scores[str(sr.class_subject_id)] = {
                            'task': 0, 'homework': 0, 'group_work': 0,
                            'project_work': 0, 'class_test': float(sr.ca_score),
                            'exam_score': float(sr.exam_score),
                            '_ca_override': float(sr.ca_score),
                        }
                
                # Create subject results from current scores
                MockSubjectResult = namedtuple('MockSubjectResult', [
                    'class_subject', 'ca_score', 'exam_score', 'total_score', 'grade', 'position'
                ])
                MockClassSubject = namedtuple('MockClassSubject', ['subject'])
                MockSubject = namedtuple('MockSubject', ['name'])
                
                subject_results = []
                total_scores_sum = 0
                subject_count = 0
                
                for class_subject_id, score_data in current_scores.items():
                    try:
                        class_subject = ClassSubject.objects.get(id=class_subject_id)
                        
                        # Calculate scores from the current form data
                        # Support _ca_override for when we load directly from DB
                        if '_ca_override' in score_data:
                            class_score = float(score_data['_ca_override'])
                        else:
                            class_score = float(score_data.get('task', 0)) + float(score_data.get('homework', 0)) + \
                                         float(score_data.get('group_work', 0)) + float(score_data.get('project_work', 0)) + \
                                         float(score_data.get('class_test', 0))
                        exam_score = float(score_data.get('exam_score', 0))
                        total_score = class_score + exam_score
                        
                        # Calculate grade using school's grade scale
                        grade_scale_a_min = getattr(school, 'grade_scale_a_min', 80)
                        grade_scale_b_min = getattr(school, 'grade_scale_b_min', 70)
                        grade_scale_c_min = getattr(school, 'grade_scale_c_min', 60)
                        grade_scale_d_min = getattr(school, 'grade_scale_d_min', 50)
                        
                        if total_score >= grade_scale_a_min:
                            grade = 'A'
                        elif total_score >= grade_scale_b_min:
                            grade = 'B'
                        elif total_score >= grade_scale_c_min:
                            grade = 'C'
                        elif total_score >= grade_scale_d_min:
                            grade = 'D'
                        else:
                            grade = 'F'
                        
                        # Create mock objects that match template structure
                        mock_subject = MockSubject(name=class_subject.subject.name)
                        mock_class_subject = MockClassSubject(subject=mock_subject)
                        
                        subject_results.append(MockSubjectResult(
                            class_subject=mock_class_subject,
                            ca_score=class_score,
                            exam_score=exam_score,
                            total_score=total_score,
                            grade=grade,
                            position=1  # Default for preview
                        ))
                        
                        total_scores_sum += total_score
                        subject_count += 1
                        
                    except ClassSubject.DoesNotExist:
                        continue
                
                # Create term result from current scores
                MockTermResult = namedtuple('MockTermResult', [
                    'average_score', 'total_score', 'class_position', 'total_students', 
                    'teacher_remarks', 'promoted'
                ])
                
                average_score = round(total_scores_sum / subject_count, 2) if subject_count > 0 else 0
                
                # Calculate real class position based on current scores
                def calculate_class_position(current_student_id, current_total_score, class_id, term_id):
                    from scores.models import SubjectResult
                    from students.models import Student
                    
                    # Get all students in the same class
                    class_students = Student.objects.filter(
                        current_class_id=class_id, 
                        is_active=True
                    ).exclude(id=current_student_id)
                    
                    better_students = 0
                    
                    for class_student in class_students:
                        # Get existing subject results for this student
                        student_results = SubjectResult.objects.filter(
                            student=class_student,
                            term_id=term_id
                        )
                        
                        if student_results.exists():
                            student_total = sum(sr.total_score for sr in student_results)
                            if student_total > current_total_score:
                                better_students += 1
                    
                    return better_students + 1
                
                class_position = calculate_class_position(
                    student.id, 
                    total_scores_sum, 
                    student.current_class_id, 
                    term_id
                ) if student.current_class_id else 1
                
                term_result = MockTermResult(
                    average_score=average_score,
                    total_score=total_scores_sum,
                    class_position=class_position,
                    total_students=student.current_class.students.count() if student.current_class else 1,
                    teacher_remarks="",  # Empty for preview with current scores
                    promoted=average_score >= getattr(school, 'grade_scale_d_min', 50)
                )
                
                # Get class teacher name
                class_teacher_name = ""
                if student.current_class and student.current_class.class_teacher:
                    class_teacher_name = student.current_class.class_teacher.get_full_name()
                
                # Calculate reopening date
                reopening_date = None
                if term.end_date:
                    from datetime import timedelta
                    reopening_date = term.end_date + timedelta(weeks=2)
                else:
                    from datetime import datetime, timedelta
                    reopening_date = datetime.now().date() + timedelta(weeks=2)
                
                # Get real attendance data
                attendance_obj = None
                try:
                    attendance_obj = Attendance.objects.get(student=student, term=term)
                except Attendance.DoesNotExist:
                    pass
                
                # Get real behavior data
                behaviour_obj = None
                try:
                    behaviour_obj = Behaviour.objects.get(student=student, term=term)
                except Behaviour.DoesNotExist:
                    pass
                
                # Prepare empty rows for table
                empty_rows_count = max(0, 9 - len(subject_results))
                empty_rows = range(empty_rows_count)
                
                # Get media URL base for logo display
                from .utils import get_media_base_url
                media_url_base = get_media_base_url(request)
                
                context = {
                    'school': school,
                    'student': student,
                    'term': term,
                    'subject_results': subject_results,
                    'term_result': term_result,
                    'attendance': attendance_obj,
                    'behaviour': behaviour_obj,
                    'class_teacher_name': class_teacher_name,
                    'reopening_date': reopening_date,
                    'position': f"{term_result.class_position}/{term_result.total_students}",
                    'empty_rows': empty_rows,
                    'is_preview': True,
                    'total_marks_ca': sum(result.ca_score for result in subject_results),
                    'total_marks_exam': sum(result.exam_score for result in subject_results),
                    'total_marks_overall': sum(result.total_score for result in subject_results),
                    'media_url_base': media_url_base
                }
                
                return render(request, 'reports/terminal_report.html', context)
                
            except Exception as e:
                return HttpResponse(
                    f'<div style="padding:20px; text-align:center;">Error processing current scores: {str(e)}</div>',
                    status=500
                )
        
        # Fallback to regular template preview with sample data
        temp_vs = ReportCardViewSet()
        temp_vs.request = request
        sample_data = temp_vs._create_sample_report_data(school)

        # Use SAME context helper as PDF generation
        html_context = temp_vs._get_sample_report_context(school, sample_data, request)

        # Default: return SAME template as PDF
        return render(request, 'reports/terminal_report.html', html_context)

    except Exception as e:
        import traceback
        return HttpResponse(f'<div style="padding:20px;">Preview error: {str(e)}<pre>{traceback.format_exc()}</pre></div>', status=500)

