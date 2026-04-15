from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Sum, Count
from .models import FeeType, FeeStructure, StudentFee, FeePayment, FeeCollection, TermBill, StudentFeeSubType
from .serializers import (
    FeeTypeSerializer, FeeStructureSerializer, StudentFeeSerializer,
    FeePaymentSerializer, FeePaymentCreateSerializer, FeeCollectionSerializer,
    StudentSearchSerializer, FeeCollectionReportSerializer,
    TermBillSerializer, GenerateBillsSerializer,
    StudentFeeSubTypeSerializer,
)
from students.models import Student
from schools.models import Class
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------

def _can_collect(user, fee_type: FeeType) -> bool:
    """Return True if this user is allowed to collect the given fee type."""
    role = getattr(user, 'role', '')
    if role in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
        return True
    if role == 'TEACHER':
        if fee_type.allow_any_teacher_collection:
            return True
        if fee_type.allow_class_teacher_collection:
            teacher = getattr(user, 'teacher', None)
            if teacher and teacher.is_class_teacher_of.exists():
                return True
    return False


class FeeTypeViewSet(viewsets.ModelViewSet):
    """Manage fee types"""
    serializer_class = FeeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = FeeType.objects.filter(school=self.request.user.school, is_active=True)
        # Optional filter: only top-level (main) fee types
        if self.request.query_params.get('top_level_only') == 'true':
            qs = qs.filter(parent_fee_type__isnull=True)
        # Optional filter: sub-types of a specific parent
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            qs = qs.filter(parent_fee_type_id=parent_id)
        return qs.prefetch_related('sub_types')

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class StudentFeeSubTypeViewSet(viewsets.ModelViewSet):
    """
    Assign students to sub-fee types.
    GET  /fees/student-sub-types/?student=<id>  – all assignments for a student
    GET  /fees/student-sub-types/?main_fee_type=<id>  – all students for a fee type
    GET  /fees/student-sub-types/?class_id=<id>  – all students in a class
    POST /fees/student-sub-types/  – create / upsert assignment
    PUT/PATCH /fees/student-sub-types/<pk>/
    DELETE /fees/student-sub-types/<pk>/
    """
    serializer_class = StudentFeeSubTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StudentFeeSubType.objects.filter(
            school=self.request.user.school
        ).select_related('student', 'main_fee_type', 'sub_fee_type')

        student_id = self.request.query_params.get('student')
        if student_id:
            qs = qs.filter(student_id=student_id)

        main_fee = self.request.query_params.get('main_fee_type')
        if main_fee:
            qs = qs.filter(main_fee_type_id=main_fee)

        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(student__current_class_id=class_id)

        return qs

    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """
        Bulk-assign multiple students at once.
        Body: { "main_fee_type": <id>, "assignments": [{"student": <id>, "sub_fee_type": <id|null>}, ...] }
        """
        main_fee_type_id = request.data.get('main_fee_type')
        assignments = request.data.get('assignments', [])
        if not main_fee_type_id:
            return Response({'error': 'main_fee_type required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            main_fee_type = FeeType.objects.get(id=main_fee_type_id, school=request.user.school)
        except FeeType.DoesNotExist:
            return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)

        results = []
        for entry in assignments:
            student_id = entry.get('student')
            sub_id = entry.get('sub_fee_type')  # may be null
            if not student_id:
                continue
            try:
                student = Student.objects.get(id=student_id, school=request.user.school)
            except Student.DoesNotExist:
                continue
            obj, _ = StudentFeeSubType.objects.update_or_create(
                student=student,
                main_fee_type=main_fee_type,
                defaults={
                    'sub_fee_type_id': sub_id,
                    'school': request.user.school,
                },
            )
            results.append(StudentFeeSubTypeSerializer(obj).data)

        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def class_roster(self, request):
        """
        Returns all students in a class with their assigned sub-fee type and computed amount
        for a given main fee type.
        GET /fees/student-sub-types/class_roster/?class_id=<id>&main_fee_type=<id>
        """
        class_id = request.query_params.get('class_id')
        main_fee_type_id = request.query_params.get('main_fee_type')
        if not class_id or not main_fee_type_id:
            return Response(
                {'error': 'class_id and main_fee_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            main_fee_type = FeeType.objects.get(id=main_fee_type_id, school=request.user.school)
        except FeeType.DoesNotExist:
            return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)

        students = Student.objects.filter(
            current_class_id=class_id,
            school=request.user.school,
            is_active=True,
        ).select_related('current_class')

        # Build lookup: student_id -> sub assignment
        assignments = {
            a.student_id: a
            for a in StudentFeeSubType.objects.filter(
                student__current_class_id=class_id,
                main_fee_type=main_fee_type,
                school=request.user.school,
            ).select_related('sub_fee_type')
        }

        # Build fee structure lookup: sub_fee_type_id -> amount (for this class level)
        level = None
        if students.exists():
            level = students.first().current_class.level

        structure_amounts = {}
        if level:
            for struct in FeeStructure.objects.filter(
                fee_type__in=main_fee_type.sub_types.all(),
                level=level,
                school=request.user.school,
            ).select_related('fee_type'):
                structure_amounts[struct.fee_type_id] = {
                    'amount': float(struct.amount),
                    'fee_type_name': struct.fee_type.name,
                }

            # Also check if the main fee itself has a direct structure (no sub-types needed)
            main_struct = FeeStructure.objects.filter(
                fee_type=main_fee_type,
                level=level,
                school=request.user.school,
                tier_label='',
            ).first()

        result = []
        for student in students:
            assignment = assignments.get(student.id)
            sub_fee = assignment.sub_fee_type if assignment else None

            # Determine amount
            if sub_fee and sub_fee.id in structure_amounts:
                amount_info = structure_amounts[sub_fee.id]
                amount = amount_info['amount']
                tier_label = sub_fee.name
            elif not main_fee_type.sub_types.exists() and level and main_struct:
                # No sub-types → use direct structure
                amount = float(main_struct.amount)
                tier_label = 'Standard'
            else:
                amount = None  # Student not assigned / no structure found
                tier_label = 'Not assigned'

            result.append({
                'student_id': student.id,
                'student_code': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'full_name': student.get_full_name(),
                'sub_fee_type_id': sub_fee.id if sub_fee else None,
                'tier_label': tier_label,
                'amount': amount,
            })

        return Response(result)


class FeeStructureViewSet(viewsets.ModelViewSet):
    """Manage fee structures"""
    serializer_class = FeeStructureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering = ['level', 'fee_type']
    
    def get_queryset(self):
        queryset = FeeStructure.objects.filter(school=self.request.user.school)
        
        # Manual filtering
        fee_type = self.request.query_params.get('fee_type')
        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)
            
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class StudentFeeViewSet(viewsets.ReadOnlyModelViewSet):
    """View student fee records"""
    serializer_class = StudentFeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['balance', 'status', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        queryset = StudentFee.objects.filter(school=self.request.user.school)
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by class if provided
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(student__current_class_id=class_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_fee_status(self, request):
        """Get summary of students by payment status"""
        queryset = self.get_queryset()
        statuses = queryset.values('status').annotate(
            count=Count('id'),
            total_balance=Sum('balance')
        )
        return Response(statuses)


class FeePaymentViewSet(viewsets.ModelViewSet):
    """Create and view fee payments"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering = ['-payment_date']
    
    def get_queryset(self):
        queryset = FeePayment.objects.filter(school=self.request.user.school)
        
        # Manual filtering
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student=student)
            
        fee_type = self.request.query_params.get('fee_type')
        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)
            
        payment_date = self.request.query_params.get('payment_date')
        if payment_date:
            queryset = queryset.filter(payment_date__date=payment_date)
        
        # If user is class teacher, show only their collections
        if hasattr(self.request.user, 'teacher') and self.request.user.teacher:
            teacher = self.request.user.teacher
            class_taught = teacher.is_class_teacher_of.first()
            if class_taught:
                queryset = queryset.filter(
                    Q(student__current_class=class_taught) |
                    Q(collected_by=self.request.user)
                )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FeePaymentCreateSerializer
        return FeePaymentSerializer
    
    @action(detail=False, methods=['post'])
    def collect_fee(self, request):
        """Collect fee from student — enforces collection permissions."""
        # Resolve fee_type and check permission before any heavy work
        fee_type_id = request.data.get('fee_type')
        if fee_type_id:
            try:
                fee_type_obj = FeeType.objects.get(id=fee_type_id, school=request.user.school)
            except FeeType.DoesNotExist:
                return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)

            if not _can_collect(request.user, fee_type_obj):
                return Response(
                    {'error': 'You do not have permission to collect this fee type.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = FeePaymentCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_fee_type(self, request):
        """Get payment summary by fee type"""
        queryset = self.get_queryset()
        summary = queryset.values('fee_type', 'fee_type__name').annotate(
            total_paid=Sum('amount_paid'),
            transactions=Count('id')
        )
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def by_class(self, request):
        """Get payment summary by class"""
        queryset = self.get_queryset()
        class_id = request.query_params.get('class_id')
        
        if not class_id:
            return Response(
                {'error': 'class_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        summary = queryset.filter(
            student__current_class_id=class_id
        ).values(
            'fee_type', 'fee_type__name'
        ).annotate(
            total_paid=Sum('amount_paid'),
            students_paid=Count('student', distinct=True)
        )
        
        return Response(summary)

    @action(detail=False, methods=['post'])
    def bulk_collect(self, request):
        """
        Teacher/admin bulk-records payments for a class collection session.

        Body:
        {
            "fee_type": <main_fee_type_id>,
            "class_id": <class_id>,
            "payments": [
                {"student": <student_id>, "amount": <float>},
                ...
            ],
            "payment_method": "CASH",   // optional, default CASH
            "notes": "..."              // optional
        }

        Returns: { "recorded": N, "total_amount": <float> }
        """
        fee_type_id = request.data.get('fee_type')
        class_id    = request.data.get('class_id')
        payments    = request.data.get('payments', [])
        method      = request.data.get('payment_method', 'CASH')
        notes       = request.data.get('notes', '')

        if not fee_type_id or not class_id:
            return Response({'error': 'fee_type and class_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fee_type_obj = FeeType.objects.get(id=fee_type_id, school=request.user.school)
        except FeeType.DoesNotExist:
            return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)

        if not _can_collect(request.user, fee_type_obj):
            return Response({'error': 'You do not have permission to collect this fee type.'}, status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone

        recorded = 0
        total_amount = 0.0

        for entry in payments:
            student_pk = entry.get('student')
            amount     = entry.get('amount')
            if not student_pk or not amount:
                continue
            try:
                amount = float(amount)
                if amount <= 0:
                    continue
                student = Student.objects.get(id=student_pk, school=request.user.school)
            except (Student.DoesNotExist, ValueError):
                continue

            # Create payment
            payment = FeePayment.objects.create(
                student=student,
                school=request.user.school,
                fee_type=fee_type_obj,
                amount_paid=amount,
                payment_method=method,
                notes=notes,
                collected_by=request.user,
            )

            # Update running StudentFee balance
            student_fee, _ = StudentFee.objects.get_or_create(
                student=student,
                school=request.user.school,
                defaults={'total_amount': 0, 'amount_paid': 0, 'balance': 0},
            )
            student_fee.amount_paid += payment.amount_paid
            student_fee.balance = student_fee.total_amount - student_fee.amount_paid
            student_fee.last_payment_date = timezone.now()
            if student_fee.balance <= 0:
                student_fee.status = 'PAID'
            elif student_fee.amount_paid > 0:
                student_fee.status = 'PARTIAL'
            student_fee.save()

            recorded += 1
            total_amount += amount

        return Response({'recorded': recorded, 'total_amount': total_amount})


class FeeCollectionViewSet(viewsets.ModelViewSet):
    """Track fee collection sessions"""
    serializer_class = FeeCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering = ['-collection_date']
    
    def get_queryset(self):
        queryset = FeeCollection.objects.filter(school=self.request.user.school)
        
        # Manual filtering
        collected_by = self.request.query_params.get('collected_by')
        if collected_by:
            queryset = queryset.filter(collected_by=collected_by)
            
        fee_type = self.request.query_params.get('fee_type')
        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)
        
        # If class teacher, show only their collections
        if hasattr(self.request.user, 'teacher') and self.request.user.teacher:
            teacher = self.request.user.teacher
            queryset = queryset.filter(collected_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, collected_by=self.request.user)


class StudentSearchForFeeViewSet(viewsets.ViewSet):
    """Search students for fee collection"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search students by name/ID"""
        query = request.query_params.get('q', '')
        class_id = request.query_params.get('class_id')
        
        if not query and not class_id:
            return Response(
                {'error': 'Provide search query or class_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build queryset
        queryset = Student.objects.filter(
            current_class__school=request.user.school
        ).select_related('user', 'current_class')
        
        # Filter by class if provided
        if class_id:
            queryset = queryset.filter(current_class_id=class_id)
        
        # Search by query
        if query:
            queryset = queryset.filter(
                Q(student_id__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__email__icontains=query)
            )
        
        # Build response with fee info
        results = []
        for student in queryset[:50]:  # Limit to 50 results
            student_fee = student.student_fee if hasattr(student, 'student_fee') else None
            
            results.append({
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.user.first_name,
                'last_name': student.user.last_name,
                'class_level': student.current_class.level if student.current_class else '',
                'section': student.current_class.section if student.current_class else '',
                'email': student.user.email,
                'phone_number': student.user.phone_number or '',
                'current_balance': float(student_fee.balance) if student_fee else 0,
                'payment_status': student_fee.status if student_fee else 'NOT_STARTED'
            })
        
        return Response(results)


class FeeReportViewSet(viewsets.ViewSet):
    """Fee collection reports"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def collection_summary(self, request):
        """Get overall collection summary"""
        school = request.user.school
        
        # Total fees outstanding
        total_outstanding = StudentFee.objects.filter(
            school=school
        ).aggregate(Sum('balance'))['balance__sum'] or 0
        
        # Total collected
        total_collected = FeePayment.objects.filter(
            school=school
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        # By fee type
        by_fee_type = FeePayment.objects.filter(
            school=school
        ).values('fee_type__name').annotate(
            total=Sum('amount_paid'),
            transactions=Count('id')
        )
        
        # By collector (teacher/admin)
        by_collector = FeePayment.objects.filter(
            school=school
        ).values(
            'collected_by__first_name',
            'collected_by__last_name'
        ).annotate(
            total=Sum('amount_paid'),
            transactions=Count('id')
        )
        
        return Response({
            'total_outstanding': float(total_outstanding),
            'total_collected': float(total_collected),
            'by_fee_type': list(by_fee_type),
            'by_collector': list(by_collector)
        })
    
    @action(detail=False, methods=['get'])
    def class_summary(self, request):
        """Get collection summary by class"""
        class_id = request.query_params.get('class_id')
        school = request.user.school
        
        if not class_id:
            return Response(
                {'error': 'class_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get class info
        try:
            cls = Class.objects.get(id=class_id, school=school)
        except Class.DoesNotExist:
            return Response(
                {'error': 'Class not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Students in class
        students = Student.objects.filter(current_class=cls)
        total_students = students.count()
        
        # Fee collection summary
        fee_summary = FeePayment.objects.filter(
            student__current_class=cls,
            school=school
        ).values('fee_type__name').annotate(
            total_collected=Sum('amount_paid'),
            students_paid=Count('student', distinct=True),
            transactions=Count('id')
        )
        
        # Payment status
        payment_status = StudentFee.objects.filter(
            student__current_class=cls,
            school=school
        ).values('status').annotate(
            count=Count('id')
        )
        
        return Response({
            'class': {
                'id': cls.id,
                'level': cls.level,
                'section': cls.section,
                'total_students': total_students
            },
            'fee_summary': list(fee_summary),
            'payment_status': list(payment_status)
        })


# ---------------------------------------------------------------------------
# Term Bills
# ---------------------------------------------------------------------------

class TermBillViewSet(viewsets.ModelViewSet):
    """Manage pre-generated term/year fee bills."""
    serializer_class = TermBillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['balance', 'status', 'amount_billed', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        qs = TermBill.objects.filter(school=self.request.user.school).select_related(
            'student__user', 'student__current_class', 'fee_type', 'term', 'term__academic_year'
        )
        term = self.request.query_params.get('term')
        if term:
            qs = qs.filter(term=term)
        fee_type = self.request.query_params.get('fee_type')
        if fee_type:
            qs = qs.filter(fee_type=fee_type)
        bill_status = self.request.query_params.get('status')
        if bill_status:
            qs = qs.filter(status=bill_status)
        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(student__current_class_id=class_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Bulk-generate TermBills for all students in the school.

        Body:
          { "term": <id>, "fee_type": <id|null>, "overwrite": false }

        For each active student → look up FeeStructure for their class level + fee_type.
        Creates a TermBill per (student, term, fee_type) combination.
        If overwrite=True an existing bill's amount_billed is updated (amount_paid preserved).
        """
        serializer = GenerateBillsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        school = request.user.school

        # Authorisation: only admins and principals may generate bills
        role = getattr(request.user, 'role', '')
        if role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response(
                {'error': 'Only school admins or principals can generate fee bills.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate term belongs to this school
        try:
            from schools.models import Term
            term = Term.objects.get(id=data['term'], academic_year__school=school)
        except Term.DoesNotExist:
            return Response({'error': 'Term not found for this school.'}, status=status.HTTP_404_NOT_FOUND)

        # Determine which fee types to generate for
        if data.get('fee_type'):
            try:
                fee_types = [FeeType.objects.get(id=data['fee_type'], school=school, is_active=True)]
            except FeeType.DoesNotExist:
                return Response({'error': 'Fee type not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Only bill-able fee types (TERM or YEAR)
            fee_types = list(FeeType.objects.filter(
                school=school, is_active=True,
                collection_frequency__in=['TERM', 'YEAR']
            ))

        if not fee_types:
            return Response(
                {'error': 'No eligible fee types found. Create TERM or YEAR fee types first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        students = Student.objects.filter(
            school=school, is_active=True
        ).select_related('current_class')

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for fee_type in fee_types:
            for student in students:
                if not student.current_class:
                    skipped_count += 1
                    continue

                # Find fee structure for student's class level
                structure = FeeStructure.objects.filter(
                    school=school,
                    fee_type=fee_type,
                    level=student.current_class.level
                ).first()

                if not structure:
                    skipped_count += 1
                    continue

                existing = TermBill.objects.filter(
                    student=student, term=term, fee_type=fee_type
                ).first()

                if existing:
                    if data.get('overwrite', False):
                        existing.amount_billed = structure.amount
                        existing.save()
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    TermBill.objects.create(
                        student=student,
                        school=school,
                        term=term,
                        fee_type=fee_type,
                        amount_billed=structure.amount,
                        amount_paid=0,
                        due_date=structure.due_date,
                        created_by=request.user,
                    )
                    created_count += 1

        return Response({
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'message': (
                f'{created_count} bills created, {updated_count} updated, '
                f'{skipped_count} skipped (no fee structure or already exists).'
            )
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Summary of TermBills grouped by fee_type and status for a given term."""
        term_id = request.query_params.get('term')
        if not term_id:
            return Response({'error': 'term parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(term=term_id)
        summary = qs.values('fee_type__name', 'status').annotate(
            count=Count('id'),
            total_billed=Sum('amount_billed'),
            total_paid=Sum('amount_paid'),
            total_balance=Sum('balance'),
        )
        return Response(list(summary))
