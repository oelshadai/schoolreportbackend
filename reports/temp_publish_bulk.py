    @action(detail=False, methods=['post'])
    def publish_bulk(self, request):
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
            
            # Check permissions for class teachers
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
                
                # Verify all students belong to teacher's classes
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
                # Admin can publish for any students in their school
                students = Student.objects.filter(
                    id__in=student_ids,
                    school=request.user.school
                )
            
            published_count = 0
            errors = []
            
            with transaction.atomic():
                for student in students:
                    try:
                        # Get or create report card
                        report_card, created = ReportCard.objects.get_or_create(
                            student=student,
                            term=term,
                            defaults={'generated_by': request.user}
                        )
                        
                        if created:
                            report_card.generate_report_code()
                        
                        # Publish the report
                        if report_card.status in ['GENERATED', 'PUBLISHED']:
                            report_card.status = 'PUBLISHED'
                            report_card.published_at = timezone.now()
                            report_card.save()
                            published_count += 1
                        else:
                            errors.append(f"{student.get_full_name()}: Report not generated yet")
                            
                    except Exception as e:
                        errors.append(f"{student.get_full_name()}: {str(e)}")
            
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