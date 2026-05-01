from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import School, AcademicYear, Term, Class, Subject, ClassSubject, GradingScale, StaffPermission
from .serializers import (
    SchoolSerializer, AcademicYearSerializer, TermSerializer,
    ClassSerializer, SubjectSerializer, ClassSubjectSerializer,
    GradingScaleSerializer, BulkAssignmentSerializer, BulkRemovalSerializer,
    SchoolSettingsSerializer, ParentPortalSettingsSerializer, ParentPortalWriteSerializer,
    StaffPermissionSerializer, SmsSettingsSerializer,
    SmsPurchaseOrderSerializer, SMS_BUNDLES,
)
from django.contrib.auth import get_user_model
from students.models import Student
from reports.models import ReportCard
from django.db import models
from django.db.models import Count

User = get_user_model()


class SchoolViewSet(viewsets.ModelViewSet):
    """School CRUD operations"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Prevent conflicts with nested routes like /api/schools/classes/ by ensuring
    # the detail lookup only matches numeric IDs (e.g., /api/schools/123/)
    lookup_value_regex = r"\d+"
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return School.objects.all()
        elif user.school:
            return School.objects.filter(id=user.school.id)
        return School.objects.none()
    
    @action(detail=True, methods=['post'])
    def setup_default_subjects(self, request, pk=None):
        """Setup default subjects for a school"""
        school = self.get_object()
        
        # Default subjects will be created via management command or admin
        return Response({"message": "Default subjects setup initiated"})


class AcademicYearViewSet(viewsets.ModelViewSet):
    """Academic Year operations"""
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return AcademicYear.objects.filter(school=user.school)
        return AcademicYear.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class TermViewSet(viewsets.ModelViewSet):
    """Term operations"""
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Term.objects.filter(academic_year__school=user.school)
        return Term.objects.none()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current term for the user's school"""
        user = request.user
        if not user.school:
            return Response(
                {"error": "User is not associated with a school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_term = Term.objects.filter(
            academic_year__school=user.school, 
            is_current=True
        ).first()
        
        if current_term:
            serializer = self.get_serializer(current_term)
            return Response(serializer.data)
        else:
            return Response(
                {"error": "No current term set. Please contact admin to configure."}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """Set a term as current"""
        term = self.get_object()
        Term.objects.filter(academic_year__school=request.user.school).update(is_current=False)
        term.is_current = True
        term.save()
        return Response({"message": "Term set as current"})


class ClassViewSet(viewsets.ModelViewSet):
    """Class operations"""
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Class.objects.filter(school=user.school)
        return Class.objects.none()
    
    def perform_create(self, serializer):
        if not getattr(self.request.user, 'school', None):
            raise permissions.PermissionDenied("User is not attached to a school")
        serializer.save(school=self.request.user.school)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students in a class"""
        class_instance = self.get_object()
        students = class_instance.students.filter(is_active=True)
        from students.serializers import StudentSerializer
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_teacher(self, request, pk=None):
        """Assign or unassign a class teacher directly (bypasses full serializer validation)"""
        class_obj = self.get_object()
        teacher_user_id = request.data.get('teacher_user_id')

        if teacher_user_id is None:
            # Unassign
            class_obj.class_teacher = None
            class_obj.save(update_fields=['class_teacher'])
            return Response({'status': 'teacher unassigned', 'class_id': class_obj.id})

        # Validate the user exists and is a TEACHER in the same school
        try:
            teacher_user = User.objects.get(pk=teacher_user_id, role='TEACHER', school=class_obj.school)
        except User.DoesNotExist:
            return Response(
                {'error': 'No active teacher with that ID found in this school'},
                status=status.HTTP_400_BAD_REQUEST
            )

        class_obj.class_teacher = teacher_user
        class_obj.save(update_fields=['class_teacher'])
        return Response({
            'status': 'teacher assigned',
            'class_id': class_obj.id,
            'teacher_user_id': teacher_user.id,
            'teacher_name': teacher_user.get_full_name(),
        })

    @action(detail=False, methods=['get'])
    def by_level(self, request):
        """Get classes filtered by level group (primary/jhs)"""
        level_group = request.query_params.get('level_group', '').upper()
        user = request.user
        
        if user.school:
            queryset = Class.objects.filter(school=user.school)
            
            if level_group == 'PRIMARY':
                # Basic 1-6
                queryset = queryset.filter(level__in=[
                    'BASIC_1', 'BASIC_2', 'BASIC_3', 'BASIC_4', 'BASIC_5', 'BASIC_6'
                ])
            elif level_group == 'JHS':
                # Basic 7-9
                queryset = queryset.filter(level__in=[
                    'BASIC_7', 'BASIC_8', 'BASIC_9'
                ])
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response([])


class SubjectViewSet(viewsets.ModelViewSet):
    """Subject operations"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClassSubjectViewSet(viewsets.ModelViewSet):
    """Class Subject assignment"""
    queryset = ClassSubject.objects.all()
    serializer_class = ClassSubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            qs = ClassSubject.objects.filter(class_instance__school=user.school)
            class_id = self.request.query_params.get('class_instance')
            # Teachers can only see subjects for classes they are assigned to.
            # When a specific class_instance is requested we allow it so teachers can
            # load subjects to enter scores — which class they can access is already
            # controlled by the /teachers/assignments/ endpoint in ScoreEntry.
            if user.role == 'TEACHER' and not class_id:
                qs = qs.filter(models.Q(class_instance__class_teacher=user) | models.Q(teacher=user))
            if class_id:
                qs = qs.filter(class_instance_id=class_id)
            subject_id = self.request.query_params.get('subject')
            if subject_id:
                qs = qs.filter(subject_id=subject_id)
            return qs
        return ClassSubject.objects.none()

    def _ensure_teacher_class_permission(self, class_obj: Class):
        user = self.request.user
        if user.role == 'TEACHER' and class_obj.class_teacher_id != user.id:
            raise permissions.PermissionDenied("You can only manage subjects for your own class")

    def perform_create(self, serializer):
        user = self.request.user
        class_id = self.request.data.get('class_instance')
        try:
            class_obj = Class.objects.get(id=class_id, school=user.school)
        except Class.DoesNotExist:
            raise permissions.PermissionDenied("Invalid class for this school")
        self._ensure_teacher_class_permission(class_obj)
        if user.role == 'TEACHER':
            # Teachers cannot introduce new subjects; admin/principal must pre-populate
            raise permissions.PermissionDenied("Teachers cannot add new subjects. Admin must assign them first.")
        # Category compatibility: PRIMARY subjects only for Basic 1-6; JHS only for Basic 7-9; BOTH allowed everywhere
        subject_id = self.request.data.get('subject')
        try:
            subject_obj = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise permissions.PermissionDenied("Invalid subject")
        level = class_obj.level
        is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
        is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
        if subject_obj.category == 'PRIMARY' and not is_primary_level:
            raise permissions.PermissionDenied("Subject is for primary classes only")
        if subject_obj.category == 'JHS' and not is_jhs_level:
            raise permissions.PermissionDenied("Subject is for JHS classes only")
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        self._ensure_teacher_class_permission(instance.class_instance)
        # Optional: ensure updated subject still matches category if subject changed
        new_subject = serializer.validated_data.get('subject')
        if new_subject:
            level = instance.class_instance.level
            is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
            is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
            if new_subject.category == 'PRIMARY' and not is_primary_level:
                raise permissions.PermissionDenied("Subject is for primary classes only")
            if new_subject.category == 'JHS' and not is_jhs_level:
                raise permissions.PermissionDenied("Subject is for JHS classes only")
        user = self.request.user
        if user.role == 'TEACHER':
            # Teachers can only claim or unclaim (set teacher to self or null). They cannot change subject or class.
            disallowed_keys = {'class_instance', 'subject'} & set(serializer.validated_data.keys())
            if disallowed_keys:
                raise permissions.PermissionDenied("Teachers cannot modify subject or class; only claim/unclaim.")
            teacher_obj = serializer.validated_data.get('teacher')
            if teacher_obj and teacher_obj.id != user.id:
                raise permissions.PermissionDenied("You can only claim a subject for yourself.")
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_teacher_class_permission(instance.class_instance)
        instance.delete()
    
    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """Bulk assign subjects to multiple classes"""
        user = request.user
        if user.role == 'TEACHER':
            return Response(
                {"detail": "Teachers cannot perform bulk operations"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        subject_ids = serializer.validated_data['subject_ids']
        class_ids = serializer.validated_data['class_ids']
        
        # Validate subjects exist and get them
        subjects = Subject.objects.filter(id__in=subject_ids)
        if len(subjects) != len(subject_ids):
            return Response(
                {"detail": "Some subjects not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate classes exist and belong to user's school
        classes = Class.objects.filter(id__in=class_ids, school=user.school)
        if len(classes) != len(class_ids):
            return Response(
                {"detail": "Some classes not found or don't belong to your school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_assignments = []
        skipped_assignments = []
        invalid_assignments = []
        
        for class_obj in classes:
            for subject in subjects:
                # Check category compatibility
                level = class_obj.level
                is_primary_level = level.startswith('BASIC_') and int(level.split('_')[1]) <= 6
                is_jhs_level = level.startswith('BASIC_') and int(level.split('_')[1]) >= 7
                
                if subject.category == 'PRIMARY' and not is_primary_level:
                    invalid_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Subject is for primary classes only'
                    })
                    continue
                if subject.category == 'JHS' and not is_jhs_level:
                    invalid_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Subject is for JHS classes only'
                    })
                    continue
                
                # Check if assignment already exists
                if ClassSubject.objects.filter(class_instance=class_obj, subject=subject).exists():
                    skipped_assignments.append({
                        'class': str(class_obj),
                        'subject': subject.name,
                        'reason': 'Already assigned'
                    })
                    continue
                
                # Create assignment
                assignment = ClassSubject.objects.create(
                    class_instance=class_obj,
                    subject=subject
                )
                created_assignments.append({
                    'id': assignment.id,
                    'class': str(class_obj),
                    'subject': subject.name
                })
        
        return Response({
            'created': created_assignments,
            'skipped': skipped_assignments,
            'invalid': invalid_assignments,
            'summary': {
                'created_count': len(created_assignments),
                'skipped_count': len(skipped_assignments),
                'invalid_count': len(invalid_assignments)
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_remove(self, request):
        """Bulk remove subjects from multiple classes"""
        user = request.user
        if user.role == 'TEACHER':
            return Response(
                {"detail": "Teachers cannot perform bulk operations"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkRemovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        subject_ids = serializer.validated_data['subject_ids']
        class_ids = serializer.validated_data['class_ids']
        
        # Get assignments to remove
        assignments = ClassSubject.objects.filter(
            class_instance__id__in=class_ids,
            subject__id__in=subject_ids,
            class_instance__school=user.school
        )
        
        removed_assignments = []
        for assignment in assignments:
            removed_assignments.append({
                'class': str(assignment.class_instance),
                'subject': assignment.subject.name
            })
        
        assignments.delete()
        
        return Response({
            'removed': removed_assignments,
            'summary': {
                'removed_count': len(removed_assignments)
            }
        })


class GradingScaleViewSet(viewsets.ModelViewSet):
    """Grading Scale operations"""
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return GradingScale.objects.filter(school=user.school)
        return GradingScale.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class SchoolDashboardView(APIView):
    """Return dashboard metrics for the current user's school"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not getattr(user, 'school', None):
            return Response({"detail": "User is not attached to a school"}, status=status.HTTP_403_FORBIDDEN)

        school = user.school
        # Counts
        students_count = Student.objects.filter(school=school).count()
        teachers_count = User.objects.filter(school=school, role='TEACHER').count()
        classes_count = Class.objects.filter(school=school).count()
        subjects_count = Subject.objects.filter(assigned_classes__class_instance__school=school).distinct().count()
        reports_count = ReportCard.objects.filter(student__school=school).count()

        # Current AY/Term
        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        current_term = Term.objects.filter(academic_year__school=school, is_current=True).first()

        # Chart data: Students per class
        classes = Class.objects.filter(school=school).annotate(student_count=Count('students'))
        students_by_class = [
            {"name": f"{c.get_level_display() or c.level}{' ' + c.section if c.section else ''}", "students": c.student_count}
            for c in classes
        ]

        # Chart data: Gender distribution
        gender_dist = Student.objects.filter(school=school).values('gender').annotate(count=Count('id'))
        gender_data = [{"name": item['gender'], "value": item['count']} for item in gender_dist]

        # Chart data: Subjects by category
        subject_category_dist = Subject.objects.filter(
            assigned_classes__class_instance__school=school
        ).values('category').annotate(count=Count('id', distinct=True))
        subjects_by_category = [{"name": item['category'], "value": item['count']} for item in subject_category_dist]

        data = {
            "school": {
                "id": school.id, 
                "name": school.name,
                "score_entry_mode": school.score_entry_mode,
                "report_template": school.report_template,
                "show_class_average": school.show_class_average,
                "show_position_in_class": school.show_position_in_class,
            },
            "counts": {
                "students": students_count,
                "teachers": teachers_count,
                "classes": classes_count,
                "subjects": subjects_count,
                "reports": reports_count,
            },
            "current": {
                "academic_year": current_year.name if current_year else None,
                "term": current_term.get_name_display() if current_term else None,
            },
            "charts": {
                "students_by_class": students_by_class,
                "gender_distribution": gender_data,
                "subjects_by_category": subjects_by_category,
            }
        }
        return Response(data)


class SchoolSettingsView(APIView):
    """Manage school settings and configuration"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current school settings"""
        user = request.user
        if not user.school:
            return Response(
                {"error": "User is not associated with a school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SchoolSettingsSerializer(user.school)
        return Response(serializer.data)
    
    def patch(self, request):
        """Update school settings"""
        user = request.user
        if not user.school:
            return Response(
                {"error": "User is not associated with a school"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has permission to modify school settings
        if not (user.is_super_admin or user.is_school_admin):
            return Response(
                {"error": "You don't have permission to modify school settings"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SchoolSettingsSerializer(
            user.school, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            school = serializer.save()
            # Sync Term.is_current with school.current_term so all parts of the
            # system that query Term.is_current=True stay in sync
            if 'current_term' in request.data and school.current_term_id:
                Term.objects.filter(academic_year__school=school).update(is_current=False)
                Term.objects.filter(id=school.current_term_id).update(is_current=True)
            return Response({
                "message": "School settings updated successfully",
                "data": serializer.data
            })
        
        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Parent Portal Settings
# ---------------------------------------------------------------------------

class ParentPortalSettingsView(APIView):
    """GET / PATCH the parent portal settings for the school."""
    permission_classes = [permissions.IsAuthenticated]

    def _require_school_admin(self, user):
        if not user.school:
            return Response({'error': 'User not associated with a school.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only school admins can manage portal settings.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def get(self, request):
        err = self._require_school_admin(request.user)
        if err:
            return err
        return Response(ParentPortalSettingsSerializer(request.user.school).data)

    def patch(self, request):
        err = self._require_school_admin(request.user)
        if err:
            return err
        serializer = ParentPortalWriteSerializer(
            request.user.school, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Parent portal settings saved.',
                'data': ParentPortalSettingsSerializer(request.user.school).data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SmsSettingsView(APIView):
    """GET / PATCH the SMS notification settings for the school."""
    permission_classes = [permissions.IsAuthenticated]

    def _require_admin(self, user):
        if not user.school:
            return Response({'error': 'User not associated with a school.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only school admins can manage SMS settings.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def get(self, request):
        err = self._require_admin(request.user)
        if err:
            return err
        return Response(SmsSettingsSerializer(request.user.school).data)

    def patch(self, request):
        err = self._require_admin(request.user)
        if err:
            return err
        serializer = SmsSettingsSerializer(request.user.school, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'SMS settings saved.',
                'data': SmsSettingsSerializer(request.user.school).data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# SMS Credit Purchase  —  admin buys credits via Paystack; balance auto-credited
# ---------------------------------------------------------------------------

class SmsPurchaseView(APIView):
    """
    GET  /schools/sms-purchase/            — list orders + current balance + bundles
    POST /schools/sms-purchase/initiate/   — create order & initiate Paystack checkout
    GET  /schools/sms-purchase/verify/     — verify Paystack ref & credit balance
    """
    permission_classes = [permissions.IsAuthenticated]

    def _require_admin(self, user):
        if not user.school:
            return Response({'error': 'User not associated with a school.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only school admins can purchase SMS credits.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def get(self, request):
        """Return SMS balance, bundles, and purchase history."""
        err = self._require_admin(request.user)
        if err:
            return err
        from .models import SmsPurchaseOrder
        orders = SmsPurchaseOrder.objects.filter(school=request.user.school).order_by('-created_at')[:20]
        return Response({
            'sms_balance': request.user.school.sms_balance,
            'sms_price_per_unit': '0.10',
            'bundles': SMS_BUNDLES,
            'orders': SmsPurchaseOrderSerializer(orders, many=True).data,
        })


class SmsPurchaseInitiateView(APIView):
    """POST /schools/sms-purchase/initiate/ — creates order + Paystack checkout."""
    permission_classes = [permissions.IsAuthenticated]

    def _require_admin(self, user):
        if not user.school:
            return Response({'error': 'User not associated with a school.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only school admins can purchase SMS credits.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def post(self, request):
        import uuid
        import requests as http_requests
        from decimal import Decimal
        from django.conf import settings as django_settings
        from .models import SmsPurchaseOrder

        err = self._require_admin(request.user)
        if err:
            return err

        school = request.user.school
        bundle_id = request.data.get('bundle_id')
        custom_units = request.data.get('custom_units')

        # Resolve sms_units and amount
        if bundle_id:
            bundle = next((b for b in SMS_BUNDLES if b['id'] == int(bundle_id)), None)
            if not bundle:
                return Response({'error': 'Invalid bundle.'}, status=status.HTTP_400_BAD_REQUEST)
            sms_units = bundle['sms_units']
            amount_ghs = Decimal(bundle['amount_ghs'])
        elif custom_units:
            try:
                sms_units = int(custom_units)
                if sms_units < 10:
                    return Response({'error': 'Minimum purchase is 10 SMS units.'}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({'error': 'Invalid custom_units.'}, status=status.HTTP_400_BAD_REQUEST)
            amount_ghs = Decimal('0.10') * sms_units
        else:
            return Response({'error': 'Provide bundle_id or custom_units.'}, status=status.HTTP_400_BAD_REQUEST)

        # Paystack platform keys
        secret_key = getattr(django_settings, 'PAYSTACK_SECRET_KEY', '')
        public_key = getattr(django_settings, 'PAYSTACK_PUBLIC_KEY', '')
        if not secret_key:
            return Response({'error': 'Payment gateway not configured. Contact support.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        payer_email = request.user.email
        if not payer_email:
            return Response({'error': 'Account email required for payment.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"SMS-{school.id}-{uuid.uuid4().hex[:10].upper()}"

        # Create pending order
        order = SmsPurchaseOrder.objects.create(
            school=school,
            requested_by=request.user,
            sms_units=sms_units,
            amount_ghs=amount_ghs,
            status=SmsPurchaseOrder.STATUS_PENDING,
            paystack_reference=reference,
        )

        # Paystack amount is in pesewas (GHS * 100)
        amount_pesewas = int(amount_ghs * 100)
        frontend_url = getattr(django_settings, 'FRONTEND_URL', '')

        payload = {
            'email': payer_email,
            'amount': amount_pesewas,
            'reference': reference,
            'currency': 'GHS',
            'metadata': {
                'order_id': order.id,
                'school_id': school.id,
                'sms_units': sms_units,
                'purchase_type': 'sms_credits',
            },
            'callback_url': f"{frontend_url}/school/sms-purchase?paystack_ref={reference}",
        }
        headers = {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        }

        try:
            resp = http_requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers, timeout=30)
            data = resp.json()
            if resp.status_code == 200 and data.get('status'):
                return Response({
                    'authorization_url': data['data']['authorization_url'],
                    'reference': reference,
                    'sms_units': sms_units,
                    'amount_ghs': str(amount_ghs),
                    'public_key': public_key,
                })
            order.status = SmsPurchaseOrder.STATUS_FAILED
            order.save(update_fields=['status'])
            return Response({'error': data.get('message', 'Paystack error')}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            order.status = SmsPurchaseOrder.STATUS_FAILED
            order.save(update_fields=['status'])
            return Response({'error': f'Payment gateway unreachable: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SmsPurchaseVerifyView(APIView):
    """GET /schools/sms-purchase/verify/?reference=<ref> — verify & auto-credit."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import requests as http_requests
        from django.conf import settings as django_settings
        from django.utils import timezone
        from django.db import transaction
        from .models import SmsPurchaseOrder

        reference = request.query_params.get('reference', '').strip()
        if not reference:
            return Response({'error': 'reference is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = SmsPurchaseOrder.objects.select_for_update().get(
                paystack_reference=reference,
                school=request.user.school,
            )
        except SmsPurchaseOrder.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Already processed — return cached result
        if order.status == SmsPurchaseOrder.STATUS_PAID:
            return Response({
                'success': True,
                'sms_units': order.sms_units,
                'new_balance': request.user.school.sms_balance,
                'message': f'{order.sms_units} SMS credits already credited.',
            })

        secret_key = getattr(django_settings, 'PAYSTACK_SECRET_KEY', '')
        headers = {'Authorization': f'Bearer {secret_key}'}
        url = f'https://api.paystack.co/transaction/verify/{reference}'

        try:
            resp = http_requests.get(url, headers=headers, timeout=30)
            data = resp.json()
        except Exception as e:
            return Response({'error': f'Cannot reach payment gateway: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not (resp.status_code == 200 and data.get('status') and data['data'].get('status') == 'success'):
            order.status = SmsPurchaseOrder.STATUS_FAILED
            order.save(update_fields=['status', 'updated_at'])
            return Response({'success': False, 'message': 'Payment not successful.'})

        # Credit the balance atomically
        with transaction.atomic():
            School.objects.filter(pk=order.school_id).update(
                sms_balance=models.F('sms_balance') + order.sms_units
            )
            order.status = SmsPurchaseOrder.STATUS_PAID
            order.credited_at = timezone.now()
            order.save(update_fields=['status', 'credited_at', 'updated_at'])

        # Refresh school to get updated balance
        order.school.refresh_from_db(fields=['sms_balance'])
        new_balance = order.school.sms_balance

        return Response({
            'success': True,
            'sms_units': order.sms_units,
            'new_balance': new_balance,
            'message': f'{order.sms_units} SMS credits added. New balance: {new_balance}',
        })


# ---------------------------------------------------------------------------
# Paystack Webhook  — server-to-server notification from Paystack
# Called by Paystack directly; HMAC-SHA512 signature verified.
# This ensures credits are applied even if the browser redirect is missed.
# ---------------------------------------------------------------------------

class PaystackWebhookView(APIView):
    """POST /schools/paystack-webhook/ — Paystack server callback."""
    authentication_classes = []  # no JWT — Paystack signs requests instead
    permission_classes = []

    def post(self, request):
        import hashlib
        import hmac
        import json
        import requests as http_requests
        from django.conf import settings as django_settings
        from django.utils import timezone
        from django.db import transaction
        from .models import SmsPurchaseOrder

        # ── Verify HMAC-SHA512 signature ───────────────────────────────────
        secret_key = getattr(django_settings, 'PAYSTACK_SECRET_KEY', '')
        paystack_signature = request.headers.get('x-paystack-signature', '')
        raw_body = request.body

        expected = hmac.new(
            secret_key.encode('utf-8'),
            raw_body,
            hashlib.sha512,
        ).hexdigest() if secret_key else ''

        if not hmac.compare_digest(expected, paystack_signature):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        # ── Parse event ────────────────────────────────────────────────────
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event', '')
        data = payload.get('data', {})

        # We only care about successful charge events for SMS purchases
        if event != 'charge.success':
            return Response({'status': 'ignored'})

        # Check metadata to confirm this is an SMS purchase
        metadata = data.get('metadata', {})
        if metadata.get('purchase_type') != 'sms_credits':
            return Response({'status': 'ignored'})

        reference = data.get('reference', '')
        if not reference:
            return Response({'status': 'ignored'})

        # ── Find and credit the order ──────────────────────────────────────
        try:
            with transaction.atomic():
                order = SmsPurchaseOrder.objects.select_for_update().get(
                    paystack_reference=reference,
                )
                if order.status == SmsPurchaseOrder.STATUS_PAID:
                    # Already credited (e.g. by the verify endpoint)
                    return Response({'status': 'already_credited'})

                School.objects.filter(pk=order.school_id).update(
                    sms_balance=models.F('sms_balance') + order.sms_units
                )
                order.status = SmsPurchaseOrder.STATUS_PAID
                order.credited_at = timezone.now()
                order.save(update_fields=['status', 'credited_at', 'updated_at'])

        except SmsPurchaseOrder.DoesNotExist:
            # Order not found — could be a non-SMS payment; ignore silently
            return Response({'status': 'ignored'})

        return Response({'status': 'ok'})


# ---------------------------------------------------------------------------
# Parent Account Management  (admin creates / lists / deletes parent accounts
# and links them to students)
# ---------------------------------------------------------------------------

class ParentManagementViewSet(viewsets.ViewSet):
    """Admin manages parent accounts and child links."""
    permission_classes = [permissions.IsAuthenticated]

    def _require_admin(self, user):
        if not user.school:
            return Response({'error': 'Not associated with a school.'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only school admins can manage parent accounts.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def list(self, request):
        """List all users who have at least one child linked for this school.
        Includes dual-role users (e.g. teachers who are also guardians).
        """
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import ParentStudent

        # Build directly from ParentStudent links scoped to this school's students
        links = (
            ParentStudent.objects
            .filter(student__school=request.user.school)
            .select_related('parent', 'student__current_class')
            .order_by('parent__last_name', 'parent__first_name')
        )

        parent_map: dict = {}
        for link in links:
            pid = link.parent_id
            if pid not in parent_map:
                p = link.parent
                parent_map[pid] = {
                    'id': p.id,
                    'name': p.get_full_name() or p.email,
                    'email': p.email,
                    'phone_number': p.phone_number or '',
                    'is_active': p.is_active,
                    'role': p.role,
                    'children': [],
                }
            s = link.student
            student_name = f"{s.first_name} {s.last_name}".strip() or s.student_id
            parent_map[pid]['children'].append({
                'link_id': link.id,
                'student_id': s.student_id,
                'student_name': student_name,
                'class': str(s.current_class) if s.current_class else '',
                'relationship': link.relationship,
                'is_primary_guardian': link.is_primary_guardian,
            })

        return Response(list(parent_map.values()))

    @action(detail=False, methods=['post'])
    def create_parent(self, request):
        """Create a parent user account and optionally link to a student."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import ParentStudent, User as UserModel

        email = request.data.get('email', '').strip().lower()
        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()
        phone = request.data.get('phone_number', '').strip()
        password = request.data.get('password', '')
        student_id = request.data.get('student_id', '').strip()
        relationship = request.data.get('relationship', 'Guardian').strip()

        if not email or not first_name or not last_name or not password:
            return Response({'error': 'email, first_name, last_name and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if UserModel.objects.filter(email=email).exists():
            return Response({'error': 'A user with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        parent = UserModel.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='PARENT',
            school=request.user.school,
            phone_number=phone or None,
        )

        link = None
        if student_id:
            from students.models import Student
            try:
                student = Student.objects.get(student_id=student_id, school=request.user.school)
                link = ParentStudent.objects.create(
                    parent=parent,
                    student=student,
                    relationship=relationship,
                    is_primary_guardian=True,
                )
            except Student.DoesNotExist:
                pass  # Account created; link skipped — admin can add link separately

        return Response({
            'id': parent.id,
            'name': parent.get_full_name(),
            'email': parent.email,
            'linked_student': link.student.student_id if link else None,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def link_child(self, request):
        """Link an existing parent account to a student."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import ParentStudent, User as UserModel
        from students.models import Student

        parent_id = request.data.get('parent_id')
        student_id = request.data.get('student_id', '').strip()
        relationship = request.data.get('relationship', 'Guardian')

        try:
            parent = UserModel.objects.get(id=parent_id, school=request.user.school, role='PARENT')
        except UserModel.DoesNotExist:
            return Response({'error': 'Parent not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            student = Student.objects.get(student_id=student_id, school=request.user.school)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        link, created = ParentStudent.objects.get_or_create(
            parent=parent, student=student,
            defaults={'relationship': relationship}
        )
        if not created:
            return Response({'error': 'This parent is already linked to that student.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'Linked {parent.get_full_name()} to student {student_id}.', 'link_id': link.id})

    @action(detail=False, methods=['delete'])
    def unlink_child(self, request):
        """Remove a parent–student link."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import ParentStudent
        link_id = request.data.get('link_id')
        try:
            link = ParentStudent.objects.get(id=link_id, parent__school=request.user.school)
            link.delete()
            return Response({'message': 'Link removed.'})
        except ParentStudent.DoesNotExist:
            return Response({'error': 'Link not found.'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """Delete a parent account or, for dual-role users, remove only their parent links."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import User as UserModel, ParentStudent
        try:
            user = UserModel.objects.get(id=pk, school=request.user.school)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.role == 'PARENT':
            user.delete()  # cascade deletes ParentStudent links
            return Response({'message': 'Parent account deleted.', 'deleted': True})
        else:
            # Dual-role user (e.g. teacher) — remove links only, keep account
            count, _ = ParentStudent.objects.filter(
                parent=user, student__school=request.user.school
            ).delete()
            return Response({
                'message': f'Removed {count} parent link(s). Account kept ({user.role} role).',
                'deleted': False,
                'links_removed': count,
            })

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Generate a new random password for a parent account and return it."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import User as UserModel
        import secrets, string

        parent_id = request.data.get('parent_id')
        try:
            parent = UserModel.objects.get(id=parent_id, school=request.user.school)
        except UserModel.DoesNotExist:
            return Response({'error': 'Parent not found.'}, status=status.HTTP_404_NOT_FOUND)

        alphabet = string.ascii_letters + string.digits + '!@#$%'
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        parent.set_password(raw_password)
        parent.save(update_fields=['password'])
        return Response({
            'email': parent.email,
            'new_password': raw_password,
        })

    @action(detail=False, methods=['get'])
    def child_summary(self, request):
        """
        Parent-facing: return a quick summary for one of their linked children.
        Query param: ?student_id=<student_id>
        """
        from accounts.models import ParentStudent
        from students.models import Student, Attendance

        student_id = request.query_params.get('student_id', '').strip()
        if not student_id:
            return Response({'error': 'student_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the requesting user has a link to this child
        linked = ParentStudent.objects.filter(
            parent=request.user, student__student_id=student_id
        ).select_related('student__current_class').first()
        if not linked:
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        student = linked.student

        # Attendance rate from most recent term record
        attendance_rate = None
        latest_att = (
            Attendance.objects.filter(student=student)
            .order_by('-term__start_date')
            .first()
        )
        if latest_att and latest_att.total_days and latest_att.total_days > 0:
            attendance_rate = round(
                (latest_att.days_present / latest_att.total_days) * 100, 1
            )

        # Recent subject scores
        recent_grades = []
        try:
            from scores.models import SubjectResult
            results = (
                SubjectResult.objects.filter(student=student)
                .select_related('class_subject__subject')
                .order_by('-term__start_date')[:10]
            )
            for r in results:
                recent_grades.append({
                    'subject': r.class_subject.subject.name,
                    'score': float(r.total_score) if r.total_score is not None else None,
                })
        except Exception:
            pass

        return Response({
            'student_id': student.student_id,
            'name': student.get_full_name(),
            'class_name': str(student.current_class) if student.current_class else '',
            'attendance_rate': attendance_rate,
            'recent_grades': recent_grades,
        })

    @action(detail=False, methods=['get'])
    def students_without_parent(self, request):
        """List students who have no parent account linked yet."""
        err = self._require_admin(request.user)
        if err:
            return err
        from students.models import Student
        from accounts.models import ParentStudent

        linked_student_ids = ParentStudent.objects.filter(
            student__school=request.user.school,
            parent__role='PARENT',
        ).values_list('student_id', flat=True)

        students = Student.objects.filter(
            school=request.user.school, is_active=True
        ).exclude(id__in=linked_student_ids).select_related('current_class')

        data = []
        for s in students:
            data.append({
                'id': s.id,
                'student_id': s.student_id,
                'name': f"{s.first_name} {s.last_name}".strip(),
                'class': s.current_class.full_name if s.current_class else '',
                'guardian_name': s.guardian_name or '',
                'guardian_email': s.guardian_email or '',
                'guardian_phone': s.guardian_phone or '',
            })
        return Response(data)

    @action(detail=False, methods=['post'])
    def create_for_student(self, request):
        """Create a parent account from an existing student's guardian info."""
        err = self._require_admin(request.user)
        if err:
            return err
        from accounts.models import ParentStudent, User as UserModel
        from students.models import Student
        import secrets, string

        student_id = request.data.get('student_id', '').strip()
        # Allow override of guardian info if admin supplies it
        override_email = request.data.get('email', '').strip().lower()
        override_first = request.data.get('first_name', '').strip()
        override_last = request.data.get('last_name', '').strip()
        override_phone = request.data.get('phone_number', '').strip()
        relationship = request.data.get('relationship', 'Guardian').strip()

        if not student_id:
            return Response({'error': 'student_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(student_id=student_id, school=request.user.school)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Resolve email and names (prefer override, fall back to student's guardian fields)
        email = override_email or (student.guardian_email or '').strip().lower()
        if not email:
            return Response({'error': 'No guardian email on file and none provided. Please supply an email.'}, status=status.HTTP_400_BAD_REQUEST)

        guardian_name = (student.guardian_name or '').strip()
        parts = guardian_name.split(' ', 1)
        first_name = override_first or (parts[0] if parts else '')
        last_name = override_last or (parts[1] if len(parts) > 1 else '')
        phone = override_phone or student.guardian_phone or ''

        existing = UserModel.objects.filter(email=email).first()
        if existing:
            # Do NOT change the stored role — a teacher/staff member may share the
            # same email as a parent.  The parent_login endpoint allows login for any
            # user that has ParentStudent links, returning role='PARENT' in the
            # response regardless of the stored role.
            #
            # Only adopt the school if the user has no school assigned yet.
            if not existing.school:
                existing.school = request.user.school
                existing.save(update_fields=['school'])

            link, _ = ParentStudent.objects.get_or_create(
                parent=existing, student=student,
                defaults={'relationship': relationship, 'is_primary_guardian': True}
            )
            note = ''
            if existing.role not in ('PARENT',):
                note = f' Note: this email belongs to a {existing.role} account — they can still log in via the parent portal.'
            return Response({
                'message': f'Account linked as parent.{note}',
                'parent_id': existing.id,
                'email': existing.email,
                'generated_password': None,
            })

        alphabet = string.ascii_letters + string.digits + '!@#$%'
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        parent = UserModel.objects.create_user(
            email=email,
            password=raw_password,
            first_name=first_name,
            last_name=last_name,
            role='PARENT',
            school=request.user.school,
            phone_number=phone or None,
        )
        ParentStudent.objects.create(
            parent=parent, student=student,
            relationship=relationship, is_primary_guardian=True,
        )
        return Response({
            'message': 'Parent account created and linked.',
            'parent_id': parent.id,
            'email': parent.email,
            'generated_password': raw_password,
        }, status=status.HTTP_201_CREATED)


class StaffPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = StaffPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.school:
            return StaffPermission.objects.none()
        return StaffPermission.objects.filter(school=user.school).select_related('teacher').prefetch_related('collect_fee_types', 'cover_classes')

    def _require_admin(self, user):
        if user.role not in ('SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)

    def create(self, request, *args, **kwargs):
        err = self._require_admin(request.user)
        if err:
            return err
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        err = self._require_admin(request.user)
        if err:
            return err
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        err = self._require_admin(request.user)
        if err:
            return err
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='my-permissions')
    def my_permissions(self, request):
        user = request.user
        if not user.school:
            return Response({'detail': 'No school attached.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            perm = StaffPermission.objects.prefetch_related('collect_fee_types', 'cover_classes').get(
                school=user.school, teacher=user
            )
        except StaffPermission.DoesNotExist:
            return Response({'detail': 'No staff permission record found.'}, status=status.HTTP_404_NOT_FOUND)
        data = StaffPermissionSerializer(perm).data
        data['school_fee_collection_enabled'] = perm.school.special_fee_collection_enabled
        data['cover_class_ids'] = list(perm.cover_classes.values_list('id', flat=True))
        data['cover_class_names'] = [{'id': c.id, 'name': c.full_name} for c in perm.cover_classes.all()]
        data['collect_fee_type_ids'] = list(perm.collect_fee_types.values_list('id', flat=True))
        return Response(data)

    @action(detail=False, methods=['patch'], url_path='toggle-school-master')
    def toggle_school_master(self, request):
        err = self._require_admin(request.user)
        if err:
            return err
        school = request.user.school
        enabled = request.data.get('enabled')
        if enabled is None:
            return Response({'error': 'enabled field required.'}, status=status.HTTP_400_BAD_REQUEST)
        school.special_fee_collection_enabled = bool(enabled)
        school.save(update_fields=['special_fee_collection_enabled'])
        return Response({'special_fee_collection_enabled': school.special_fee_collection_enabled})

    @action(detail=True, methods=['patch'], url_path='toggle')
    def toggle_teacher(self, request, pk=None):
        err = self._require_admin(request.user)
        if err:
            return err
        perm = self.get_object()
        enabled = request.data.get('fee_collection_enabled')
        if enabled is None:
            return Response({'error': 'fee_collection_enabled field required.'}, status=status.HTTP_400_BAD_REQUEST)
        perm.fee_collection_enabled = bool(enabled)
        perm.save(update_fields=['fee_collection_enabled'])
        return Response({'fee_collection_enabled': perm.fee_collection_enabled})

    @action(detail=False, methods=['get'], url_path='teachers-list')
    def teachers_list(self, request):
        err = self._require_admin(request.user)
        if err:
            return err
        UserModel = get_user_model()
        teachers = UserModel.objects.filter(
            school=request.user.school, role='TEACHER', is_active=True
        ).order_by('first_name', 'last_name')
        return Response([{'id': t.id, 'name': t.get_full_name() or t.username, 'email': t.email} for t in teachers])
