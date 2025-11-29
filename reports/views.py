from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from .models import ReportCard
from .serializers import ReportCardSerializer
from .pdf_generator import ReportGenerator
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
            
            # Generate PDF
            generator = ReportGenerator(student, student.school, term)
            pdf_buffer = generator.generate_pdf(
                subject_results,
                term_result,
                attendance,
                behaviour,
                report_card.report_code
            )
            
            # Generate QR code
            qr_buffer = generator.generate_qr_code(report_card.report_code)
            
            # Save files
            pdf_filename = f"report_card_{student.student_id}_{term.id}.pdf"
            qr_filename = f"qr_{report_card.report_code}.png"
            
            report_card.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.read()), save=False)
            report_card.qr_code.save(qr_filename, ContentFile(qr_buffer.read()), save=False)
            
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
            }
            
            # Render HTML template
            html_content = render_to_string('reports/terminal_report_template.html', context)
            
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
                'class_test', 'exam_score', 'total_score', 'class_score', 'grade', 'position'
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
                        class_score=class_score,
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
                        'class_score': result.class_score,
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
                print(f"Authentication successful for user: {user.email}")
            except (InvalidToken, TokenError) as e:
                print(f"Token authentication failed: {e}")
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
            
            print(f"Preview request for ID: {preview_id}")
            
            # Get preview data from cache instead of session
            from django.core.cache import cache
            preview_data = cache.get(preview_id)
            if not preview_data:
                print(f"No preview data found in cache for ID: {preview_id}")
                return HttpResponse(
                    "<h1>Preview Not Found</h1><p>Preview data not found or expired. Please generate a new preview.</p>",
                    status=404
                )
            
            print(f"Found preview data: {preview_data}")
            
            # Verify user has access to this preview
            if not request.user.is_authenticated or request.user.id != preview_data.get('user_id'):
                return HttpResponse(
                    "<h1>Access Denied</h1><p>You don't have permission to view this preview.</p>",
                    status=403
                )
            
            student = Student.objects.get(id=preview_data['student_id'], school_id=preview_data['school_id'])
            term = Term.objects.get(id=preview_data['term_id'])
            
            print(f"Student: {student.get_full_name()}, Term: {term}")
            
            # Create mock objects from session data
            MockSubjectResult = namedtuple('MockSubjectResult', [
                'class_subject', 'class_score', 'exam_score', 'total_score', 'grade', 'position'
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
                    class_score=result_data['class_score'],
                    exam_score=result_data['exam_score'],
                    total_score=result_data['total_score'],
                    grade=result_data['grade'],
                    position=result_data['position']
                )
                subject_results.append(mock_result)
            
            print(f"Created {len(subject_results)} mock subject results")
            
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
            
            print(f"Rendering template with context keys: {context.keys()}")
            
            # Render HTML template
            from django.shortcuts import render
            response = render(request, 'reports/terminal_report_template.html', context)
            # Remove X-Frame-Options to allow iframe embedding from frontend
            return response
            
        except Exception as e:
            print(f"Preview error: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            response = HttpResponse(
                f"<h1>Preview Error</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>",
                status=500
            )
            # Remove X-Frame-Options to allow iframe embedding from frontend
            return response

    @action(detail=False, methods=['get'], url_path='terminal-report-preview/(?P<term_result_id>[^/.]+)')
    def terminal_report_preview(self, request, term_result_id=None):
        """Preview terminal report as HTML"""
        try:
            from django.template.loader import render_to_string
            from datetime import datetime, timedelta
            
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
            
            # Get subject results
            subject_results = SubjectResult.objects.filter(
                student=student,
                term=term
            ).select_related('class_subject__subject')
            
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
            empty_rows_count = max(0, 9 - subject_results.count())
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
            }
            
            # Render HTML template
            from django.shortcuts import render
            return render(request, 'reports/terminal_report_template.html', context)
            
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
                    # Generate report for each student
                    subject_results = SubjectResult.objects.filter(student=student, term=term)
                    
                    if not subject_results.exists():
                        errors.append(f"No results for {student.get_full_name()}")
                        continue
                    
                    term_result = TermResult.objects.filter(student=student, term=term).first()
                    if not term_result:
                        errors.append(f"No term result computed for {student.get_full_name()}")
                        continue
                        
                    attendance = Attendance.objects.filter(student=student, term=term).first()
                    behaviour = Behaviour.objects.filter(student=student, term=term).first()
                    
                    report_card, created = ReportCard.objects.get_or_create(
                        student=student,
                        term=term,
                        defaults={'generated_by': request.user}
                    )
                    
                    if created:
                        report_card.generate_report_code()
                    
                    generator = ReportGenerator(student, student.school, term)
                    pdf_buffer = generator.generate_pdf(
                        subject_results, term_result, attendance, behaviour, report_card.report_code
                    )
                    
                    qr_buffer = generator.generate_qr_code(report_card.report_code)
                    
                    pdf_filename = f"report_card_{student.student_id}_{term.id}.pdf"
                    qr_filename = f"qr_{report_card.report_code}.png"
                    
                    report_card.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.read()), save=False)
                    report_card.qr_code.save(qr_filename, ContentFile(qr_buffer.read()), save=False)
                    
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
    
    @action(detail=False, methods=['get'])
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
            # Check for token in query params for preview links
            token_param = request.GET.get('token')
            if token_param and not request.user.is_authenticated:
                from rest_framework_simplejwt.tokens import UntypedToken
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                from django.contrib.auth import get_user_model
                
                try:
                    UntypedToken(token_param)
                    from rest_framework_simplejwt.authentication import JWTAuthentication
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(token_param)
                    user = jwt_auth.get_user(validated_token)
                    request.user = user
                except (InvalidToken, TokenError):
                    return Response(
                        {"error": "Invalid token"},
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
            
            # Generate HTML preview
            html_context = {
                'school': school,
                'student': sample_data['student'],
                'student_name': sample_data['student'].get_full_name() if hasattr(sample_data['student'], 'get_full_name') else f"{sample_data['student'].first_name} {sample_data['student'].last_name}",
                'term': sample_data['term'],
                'subject_results': sample_data['subject_results'],
                'term_result': sample_data['term_result'],
                'attendance': sample_data['attendance'],
                'behaviour': sample_data['behaviour'],
                'is_preview': True
            }

            if request.GET.get('format') == 'pdf':
                # Render via ReportGenerator to PDF buffer
                from .pdf_generator import ReportGenerator
                generator = ReportGenerator(sample_data['student'], school, sample_data['term'])
                # Build minimal objects the generator expects
                class ResultObj:
                    def __init__(self, subject, class_score_50, exam_score_50):
                        self.class_subject = type('X', (), {'subject': type('S', (), {'name': subject})()})
                        # Generator computes class_score as sum/2, so double the 50% score here
                        self.task = class_score_50 * 2
                        self.homework = 0
                        self.group_work = 0
                        self.project_work = 0
                        self.class_test = 0
                        self.exam_score = exam_score_50

                subject_results = []
                for r in sample_data['subject_results']:
                    subject_results.append(ResultObj(r.subject_name, r.class_score, r.exam_score))

                pdf_buffer = generator.generate_pdf(
                    subject_results,
                    sample_data['term_result'],
                    sample_data['attendance'],
                    sample_data['behaviour'],
                    'PREVIEW'
                )
                response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="template_preview.pdf"'
                return response
            else:
                html_content = render_to_string('reports/terminal_report_template.html', html_context)
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
            
            # Create sample data for preview
            sample_data = self._create_sample_report_data(school)
            
            # Convert namedtuples to dictionaries for JSON serialization
            response_data = {
                'school': {
                    'name': school.name,
                    'address': school.address,
                    'phone_number': school.phone_number,
                    'motto': school.motto,
                    'current_academic_year': getattr(school, 'current_academic_year', ''),
                    'report_template': school.report_template,
                    'show_position_in_class': getattr(school, 'show_position_in_class', True),
                    'show_student_photos': getattr(school, 'show_student_photos', True),
                    'class_teacher_signature_required': getattr(school, 'class_teacher_signature_required', False),
                    'show_headteacher_signature': getattr(school, 'show_headteacher_signature', True),
                    'grade_scale_a_min': school.grade_scale_a_min,
                    'grade_scale_b_min': school.grade_scale_b_min,
                    'grade_scale_c_min': school.grade_scale_c_min,
                    'grade_scale_d_min': school.grade_scale_d_min,
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
                    'academic_year': sample_data['term'].academic_year,
                },
                'subject_results': [
                    {
                        'subject_name': result.subject_name,
                        'class_score': result.class_score,
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
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate preview data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_sample_report_data(self, school):
        """Create sample data for template preview"""
        from collections import namedtuple
        import random
        
        # Sample student data
        class SampleStudent:
            def __init__(self, school):
                self.student_id = "STU001"
                self.first_name = "Sample"
                self.last_name = "Student" 
                self.date_of_birth = "2010-01-15"
                self.photo = None
                self.school = school
                # Add comprehensive current_class mock
                class MockClass:
                    def __init__(self):
                        self.name = "JSS 1A"
                        self.id = 1
                        self.level = "JHS"
                        self.class_teacher = None
                        
                    class Students:
                        def count(self):
                            return 25
                    
                    students = Students()
                self.current_class = MockClass()
                self.current_class_id = 1
            
            def get_full_name(self):
                return f"{self.first_name} {self.last_name}"
        
        sample_student = SampleStudent(school)
        
        # Sample term data with proper academic year
        class SampleTerm:
            def __init__(self):
                self.name = "First Term"
                self.id = 1
                self.start_date = None
                self.end_date = None
                
                class MockAcademicYear:
                    def __init__(self):
                        self.name = "2024/2025"
                        self.id = 1
                
                self.academic_year = MockAcademicYear()
        
        sample_term = SampleTerm()
        
        # Sample subject results
        subjects = ['English Language', 'Mathematics', 'Science', 'Social Studies', 'ICT']
        SampleSubjectResult = namedtuple('SampleSubjectResult', ['subject_name', 'class_score', 'exam_score', 'total_score', 'grade', 'position'])
        
        sample_results = []
        for i, subject in enumerate(subjects):
            # Keep scores within 0-50 each to reflect 50/50 weighting
            class_score = random.randint(20, 30)  # class component (already out of 50 for preview)
            exam_score = random.randint(25, 50)   # exam component (out of 50)
            total = class_score + exam_score
            
            if total >= school.grade_scale_a_min:
                grade = 'A'
            elif total >= school.grade_scale_b_min:
                grade = 'B'
            elif total >= school.grade_scale_c_min:
                grade = 'C'
            elif total >= school.grade_scale_d_min:
                grade = 'D'
            else:
                grade = 'F'
            
            sample_results.append(SampleSubjectResult(
                subject_name=subject,
                class_score=class_score,
                exam_score=exam_score,
                total_score=total,
                grade=grade,
                position=i + 1
            ))
        
        # Sample term result
        SampleTermResult = namedtuple('SampleTermResult', ['total_score', 'average', 'position', 'grade', 'status'])
        total_scores = sum(result.total_score for result in sample_results)
        average = total_scores / len(sample_results) if sample_results else 0
        
        sample_term_result = SampleTermResult(
            total_score=total_scores,
            average=round(average, 2),
            position=5,
            grade='B' if average >= school.grade_scale_b_min else 'C',
            status='PROMOTED' if average >= school.grade_scale_d_min else 'REPEAT'
        )
        
        # Sample attendance
        SampleAttendance = namedtuple('SampleAttendance', ['days_present', 'days_absent', 'total_days'])
        sample_attendance = SampleAttendance(
            days_present=85,
            days_absent=5,
            total_days=90
        )
        
        # Sample behaviour with all required fields
        SampleBehaviour = namedtuple('SampleBehaviour', ['conduct', 'attitude', 'interest', 'class_teacher_remarks'])
        sample_behaviour = SampleBehaviour(
            conduct='GOOD',
            attitude='EXCELLENT',
            interest='VERY GOOD',
            class_teacher_remarks='Student has shown good progress this term. Continue to work hard and maintain good behavior.'
        )
        sample_behaviour = SampleBehaviour(
            conduct='Good',
            interest='Very Good',
            class_teacher_remarks='Student shows excellent potential and good behavior in class.'
        )
        
        return {
            'student': sample_student,
            'term': sample_term,
            'subject_results': sample_results,
            'term_result': sample_term_result,
            'attendance': sample_attendance,
            'behaviour': sample_behaviour
        }


from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def template_preview_pdf(request):
    """Standalone endpoint for template preview (HTML or PDF). Allows iframe embedding."""
    from django.http import HttpResponse, JsonResponse
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    # Authenticate via Authorization header already handled by middleware OR token query param
    if not request.user.is_authenticated:
        token_param = request.GET.get('token')
        if token_param:
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token_param)
                user = jwt_auth.get_user(validated)
                request.user = user
            except (InvalidToken, TokenError):
                return JsonResponse({'error': 'Invalid token'}, status=401)
        else:
            return JsonResponse({'error': 'Authentication required'}, status=401)

    school = getattr(request.user, 'school', None)
    if not school:
        return JsonResponse({'error': 'User must be associated with a school'}, status=400)

    # Reuse helper via a temporary viewset instance
    temp_vs = ReportCardViewSet()
    sample_data = temp_vs._create_sample_report_data(school)

    fmt = request.GET.get('format', 'html')
    context = {
        'school': school,
        'student': sample_data['student'],
        'term': sample_data['term'],
        'subject_results': sample_data['subject_results'],
        'term_result': sample_data['term_result'],
        'attendance': sample_data['attendance'],
        'behaviour': sample_data['behaviour'],
        'is_preview': True
    }

    if fmt == 'pdf':
        from .pdf_generator import ReportGenerator
        class ResultObj:
            def __init__(self, subject, class_score_50, exam_score_50):
                self.class_subject = type('X', (), {'subject': type('S', (), {'name': subject})()})
                # Double class score so generator's sum/2 -> 50% value
                self.task = class_score_50 * 2
                self.homework = 0
                self.group_work = 0
                self.project_work = 0
                self.class_test = 0
                self.exam_score = exam_score_50

        subj_results = [ResultObj(r.subject_name, r.class_score, r.exam_score) for r in sample_data['subject_results']]
        generator = ReportGenerator(sample_data['student'], school, sample_data['term'])
        pdf_buffer = generator.generate_pdf(
            subj_results,
            sample_data['term_result'],
            sample_data['attendance'],
            sample_data['behaviour'],
            'PREVIEW'
        )
        resp = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="template_preview.pdf"'
        return resp
    else:
        from django.template.loader import render_to_string
        html = render_to_string('reports/preview_template.html', context)
        return HttpResponse(html, content_type='text/html')
