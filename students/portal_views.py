from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Student


def _get_student(request):
    return Student.objects.select_related('current_class', 'school').get(user=request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_classes(request):
    """Return the student's current class info."""
    try:
        student = _get_student(request)
        cls = student.current_class
        if not cls:
            return Response([])
        data = {
            'id': cls.id,
            'level': cls.level,
            'level_display': cls.get_level_display(),
            'section': cls.section,
            'full_name': str(cls),
            'class_teacher': cls.class_teacher.get_full_name() if cls.class_teacher else None,
        }
        return Response([data])
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_subjects(request, class_id=None):
    """Return subjects for the student's class."""
    try:
        from schools.models import ClassSubject
        student = _get_student(request)
        target_class_id = class_id or (student.current_class.id if student.current_class else None)
        if not target_class_id:
            return Response([])
        subjects = ClassSubject.objects.filter(
            class_instance_id=target_class_id
        ).select_related('subject', 'teacher')
        data = [
            {
                'id': cs.id,
                'subject': cs.subject.name,
                'code': cs.subject.code,
                'teacher': cs.teacher.get_full_name() if cs.teacher else None,
            }
            for cs in subjects
        ]
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_announcements(request, class_id=None):
    """Return announcements for the student's school."""
    try:
        from announcements.models import Announcement
        announcements = Announcement.objects.filter(
            school=request.user.school
        ).order_by('-created_at')[:20]
        data = [
            {
                'id': a.id,
                'title': a.title,
                'content': a.content,
                'priority': getattr(a, 'priority', 'normal'),
                'created_at': a.created_at.isoformat(),
            }
            for a in announcements
        ]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_profile(request):
    """Return the student's profile data."""
    try:
        student = _get_student(request)
        data = {
            'id': student.id,
            'student_id': student.student_id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'other_names': student.other_names or '',
            'full_name': student.get_full_name(),
            'gender': student.gender,
            'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
            'email': student.user.email if student.user else None,
            'photo': student.photo.url if student.photo else None,
            'current_class': str(student.current_class) if student.current_class else None,
            'class_id': student.current_class.id if student.current_class else None,
            'school': student.school.name if student.school else None,
            'guardian_name': student.guardian_name,
            'guardian_phone': student.guardian_phone,
            'guardian_email': student.guardian_email,
            'guardian_address': student.guardian_address,
            'admission_date': student.admission_date.isoformat() if student.admission_date else None,
            'is_active': student.is_active,
        }
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_assignments_list(request):
    """Return the student's assignments."""
    try:
        from assignments.models import StudentAssignment
        student = _get_student(request)
        assignments = StudentAssignment.objects.filter(
            student=student
        ).select_related(
            'assignment', 'assignment__class_subject__subject'
        ).order_by('-assignment__due_date')[:50]
        data = [
            {
                'id': sa.id,
                'title': sa.assignment.title,
                'subject': sa.assignment.class_subject.subject.name if sa.assignment.class_subject else None,
                'assignment_type': sa.assignment.assignment_type,
                'due_date': sa.assignment.due_date.isoformat() if sa.assignment.due_date else None,
                'status': sa.status,
                'score': float(sa.score) if sa.score is not None else None,
                'max_score': sa.assignment.max_score,
                'submitted_at': sa.submitted_at.isoformat() if sa.submitted_at else None,
            }
            for sa in assignments
        ]
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_schedule(request):
    """Return the student's class schedule (subjects with teachers)."""
    try:
        from schools.models import ClassSubject
        student = _get_student(request)
        if not student.current_class:
            return Response([])
        subjects = ClassSubject.objects.filter(
            class_instance=student.current_class
        ).select_related('subject', 'teacher')
        data = [
            {
                'id': cs.id,
                'subject': cs.subject.name,
                'code': cs.subject.code,
                'teacher': cs.teacher.get_full_name() if cs.teacher else None,
            }
            for cs in subjects
        ]
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_reports(request):
    """Return the student's term results."""
    try:
        from scores.models import TermResult, SubjectResult
        student = _get_student(request)
        term_results = TermResult.objects.filter(
            student=student
        ).select_related('term', 'term__academic_year', 'class_instance').order_by('-term__start_date')

        data = []
        for tr in term_results:
            subject_results = SubjectResult.objects.filter(
                student=student, term=tr.term
            ).select_related('class_subject__subject')
            subjects = [
                {
                    'subject_name': sr.class_subject.subject.name,
                    'ca_score': float(sr.ca_score),
                    'exam_score': float(sr.exam_score),
                    'total_score': float(sr.total_score),
                    'grade': sr.grade,
                    'remark': sr.remark,
                }
                for sr in subject_results
            ]
            data.append({
                'id': tr.id,
                'student_id': student.id,
                'term_id': tr.term.id,
                'term': str(tr.term),
                'term_name': tr.term.get_name_display(),
                'academic_year': tr.term.academic_year.name,
                'class_name': str(tr.class_instance),
                'total_score': float(tr.total_score),
                'average_score': float(tr.average_score),
                'subjects_count': tr.subjects_count,
                'class_position': tr.class_position,
                'total_students': tr.total_students,
                'promoted': tr.promoted,
                'teacher_remarks': tr.teacher_remarks,
                'principal_remarks': tr.principal_remarks,
                'subjects': subjects,
            })
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_published_reports(request):
    """Return the student's published report cards."""
    try:
        from reports.models import ReportCard
        student = _get_student(request)
        
        published_reports = ReportCard.objects.filter(
            student=student,
            status='PUBLISHED'
        ).select_related('term', 'term__academic_year').order_by('-term__start_date')
        
        data = []
        for report in published_reports:
            data.append({
                'id': report.id,
                'student_id': student.id,
                'term_id': report.term.id,
                'term_name': report.term.get_name_display(),
                'academic_year': report.term.academic_year.name,
                'status': report.status,
                'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                'published_at': report.published_at.isoformat() if report.published_at else None,
                'report_code': report.report_code,
                'pdf_url': report.pdf_file.url if report.pdf_file else None,
            })
        
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_student_report(request, report_id):
    """Return a single term result by ID."""
    try:
        from scores.models import TermResult, SubjectResult
        student = _get_student(request)
        tr = TermResult.objects.select_related(
            'term', 'term__academic_year', 'class_instance'
        ).get(id=report_id, student=student)

        subject_results = SubjectResult.objects.filter(
            student=student, term=tr.term
        ).select_related('class_subject__subject')

        subjects = [
            {
                'subject': sr.class_subject.subject.name,
                'ca_score': float(sr.ca_score),
                'exam_score': float(sr.exam_score),
                'total_score': float(sr.total_score),
                'grade': sr.grade,
                'remark': sr.remark,
            }
            for sr in subject_results
        ]
        data = {
            'id': tr.id,
            'term': str(tr.term),
            'term_name': tr.term.get_name_display(),
            'academic_year': tr.term.academic_year.name,
            'class': str(tr.class_instance),
            'total_score': float(tr.total_score),
            'average_score': float(tr.average_score),
            'subjects_count': tr.subjects_count,
            'class_position': tr.class_position,
            'total_students': tr.total_students,
            'promoted': tr.promoted,
            'teacher_remarks': tr.teacher_remarks,
            'principal_remarks': tr.principal_remarks,
            'student': {
                'name': student.get_full_name(),
                'student_id': student.student_id,
                'school': student.school.name if student.school else None,
            },
            'subjects': subjects,
        }
        return Response(data)
    except TermResult.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def view_student_published_report(request, term_id):
    """View a published report card for the authenticated student.
    
    Accepts authentication either via:
    - Standard Authorization header (Bearer <token>)
    - ?token=<jwt> query parameter (for iframe embedding, same as template_preview_public)
    """
    from django.http import HttpResponse
    from django.shortcuts import render
    from reports.models import ReportCard
    from scores.models import SubjectResult, TermResult
    from students.models import Attendance, Behaviour

    # Authenticate via Authorization header or ?token= query param
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
                    '<div style="padding:20px;text-align:center;font-family:Arial,sans-serif;">'
                    '<h3>Session Expired</h3><p>Please log in again to view your report.</p></div>',
                    status=401
                )
        else:
            return HttpResponse(
                '<div style="padding:20px;text-align:center;font-family:Arial,sans-serif;">'
                '<h3>Authentication Required</h3><p>Please log in to view your report.</p></div>',
                status=401
            )

    try:
        student = _get_student(request)
        
        # Get the published report card for this student and term
        report_card = ReportCard.objects.select_related(
            'term', 
            'term__academic_year',
            'student__school'
        ).get(
            student=student,
            term_id=term_id,
            status='PUBLISHED'
        )
        
        # Use the EXACT same context generation logic as the teacher's _get_report_context
        term = report_card.term
        
        # Get all required data with the same queries as the main system
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
        
        # Calculate total marks for template (using correct field name)
        total_marks_ca = sum(sr.ca_score for sr in subject_results) if subject_results else 0
        total_marks_exam = sum(sr.exam_score for sr in subject_results) if subject_results else 0
        total_marks_overall = total_marks_ca + total_marks_exam
        
        # Import the EXACT same utilities as the teacher system
        from reports.utils import get_media_base_url
        media_url_base = get_media_base_url(request)
        
        # Create the EXACT same context as the teacher's _get_report_context method
        context = {
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
        
        # Return the HTML response using the SAME template as the teacher system
        response = render(request, 'reports/terminal_report.html', context)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
        
    except ReportCard.DoesNotExist:
        return HttpResponse(
            '<div style="padding:20px; text-align:center; font-family:Arial,sans-serif;">'
            '<h3>Report Not Found</h3>'
            '<p>This report is not available or not yet published.</p>'
            '</div>',
            status=404
        )
    except Student.DoesNotExist:
        return HttpResponse(
            '<div style="padding:20px; text-align:center; font-family:Arial,sans-serif;">'
            '<h3>Student Profile Not Found</h3>'
            '<p>Please contact your school administrator.</p>'
            '</div>',
            status=404
        )
    except Exception as e:
        import traceback
        return HttpResponse(
            f'<div style="padding:20px; text-align:center; font-family:Arial,sans-serif;">'
            f'<h3>Error Loading Report</h3>'
            f'<p>An error occurred while loading your report.</p>'
            f'<details><summary>Technical Details</summary>'
            f'<pre style="text-align:left; font-size:12px;">{str(e)}\n\n{traceback.format_exc()}</pre>'
            f'</details>'
            f'</div>',
            status=500
        )
