from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .models import ReportCard
from students.models import Student
from schools.models import Term


def _publish_bulk_impl(viewset, request):
    """Publish multiple report cards at once"""
    student_ids = request.data.get('student_ids', [])
    term_id = request.data.get('term_id')

    if not student_ids or not term_id:
        return Response(
            {"error": "student_ids and term_id are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        term = Term.objects.get(id=term_id)

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

            teacher_class_ids = teacher_classes.values_list('id', flat=True)
            students = Student.objects.filter(
                id__in=student_ids,
                school=request.user.school,
                current_class_id__in=teacher_class_ids
            )

            if students.count() != len(student_ids):
                return Response(
                    {"error": "You can only publish reports for students in your assigned classes"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            students = Student.objects.filter(
                id__in=student_ids,
                school=request.user.school
            )

        published_count = 0
        errors = []

        with transaction.atomic():
            for student in students:
                try:
                    report_card, created = ReportCard.objects.get_or_create(
                        student=student,
                        term=term,
                        defaults={'generated_by': request.user}
                    )

                    if created:
                        report_card.generate_report_code()

                    # Publish regardless of current status (DRAFT, GENERATED, or re-publish)
                    report_card.status = 'PUBLISHED'
                    report_card.published_at = timezone.now()
                    report_card.save()
                    published_count += 1

                    # Auto-compute TermResult so students can see scores in their portal
                    try:
                        from scores.models import TermResult
                        term_result, _ = TermResult.objects.update_or_create(
                            student=student,
                            term=term,
                            defaults={'class_instance': student.current_class}
                        )
                        term_result.calculate_aggregate()
                        term_result.generate_teacher_remarks()
                    except Exception:
                        pass  # Don't fail publish if term result computation fails

                except Exception as e:
                    errors.append(f"{student.get_full_name()}: {str(e)}")

            # Compute class positions for all students in each affected class
            try:
                from scores.models import TermResult, SubjectResult
                class_ids = set(
                    s.current_class_id for s in students if s.current_class_id
                )
                for class_id in class_ids:
                    # Overall class positions
                    class_term_results = list(
                        TermResult.objects.filter(
                            term=term,
                            class_instance_id=class_id
                        ).order_by('-average_score', 'student__first_name')
                    )
                    total = len(class_term_results)
                    for position, tr in enumerate(class_term_results, start=1):
                        tr.class_position = position
                        tr.total_students = total
                        tr.save(update_fields=['class_position', 'total_students'])

                    # Per-subject positions within this class for this term
                    class_student_ids = [tr.student_id for tr in class_term_results]
                    subject_ids = SubjectResult.objects.filter(
                        term=term,
                        student_id__in=class_student_ids
                    ).values_list('class_subject_id', flat=True).distinct()

                    for subject_id in subject_ids:
                        subject_results = list(
                            SubjectResult.objects.filter(
                                term=term,
                                class_subject_id=subject_id,
                                student_id__in=class_student_ids
                            ).order_by('-total_score', 'student__first_name')
                        )
                        for pos, sr in enumerate(subject_results, start=1):
                            sr.position = pos
                            sr.save(update_fields=['position'])
            except Exception:
                pass  # Don't fail publish if position calculation fails

        return Response({
            "message": f"Successfully published {published_count} reports",
            "published_count": published_count,
            "errors": errors
        })

    except Term.DoesNotExist:
        return Response(
            {"error": "Term not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to publish reports: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
