from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.conf import settings as django_settings
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
            # Class.class_teacher is a direct FK to User
            from schools.models import Class as SchoolClass
            if SchoolClass.objects.filter(class_teacher=user).exists():
                return True
        # Special fee collector via StaffPermission
        from schools.models import StaffPermission
        try:
            perm = StaffPermission.objects.get(school=user.school, teacher=user)
            if (perm.can_collect_fees and perm.fee_collection_enabled
                    and user.school.special_fee_collection_enabled):
                assigned = perm.collect_fee_types.all()
                if not assigned.exists() or assigned.filter(id=fee_type.id).exists():
                    return True
        except StaffPermission.DoesNotExist:
            pass
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

        # Today's already-collected payments for this fee type + class
        from django.utils import timezone
        today = timezone.localdate()
        today_payments = {}
        for p in FeePayment.objects.filter(
            school=request.user.school,
            fee_type=main_fee_type,
            student__current_class_id=class_id,
            payment_date__date=today,
        ).values('student_id').annotate(paid_today=Sum('amount_paid')):
            today_payments[p['student_id']] = float(p['paid_today'])

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
                'paid_today': today_payments.get(student.id, 0),
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
        from decimal import Decimal

        recorded = 0
        total_amount = Decimal('0')

        for entry in payments:
            student_pk = entry.get('student')
            amount     = entry.get('amount')
            if not student_pk or not amount:
                continue
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    continue
                student = Student.objects.get(id=student_pk, school=request.user.school)
            except (Student.DoesNotExist, ValueError, Exception):
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
                defaults={'total_amount': Decimal('0'), 'amount_paid': Decimal('0'), 'balance': Decimal('0')},
            )
            student_fee.amount_paid += payment.amount_paid
            # Clamp balance to 0 — overpayments are not a debt
            balance = student_fee.total_amount - student_fee.amount_paid
            student_fee.balance = balance if balance > Decimal('0') else Decimal('0')
            student_fee.last_payment_date = timezone.now()
            if student_fee.total_amount > 0 and student_fee.balance <= 0:
                student_fee.status = 'PAID'
            elif student_fee.amount_paid > 0:
                student_fee.status = 'PARTIAL'
            student_fee.save()

            recorded += 1
            total_amount += amount

        return Response({'recorded': recorded, 'total_amount': float(total_amount)})


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

        # --- Daily fee stats ---
        # Collected: sum of payments whose fee_type is DAILY
        daily_collected = FeePayment.objects.filter(
            school=school,
            fee_type__collection_frequency='DAILY',
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        # Expected daily fees: for each active DAILY fee type, sum the
        # FeeStructure amount × number of active students at that level.
        from django.db.models import IntegerField
        from django.db.models.functions import Cast
        from students.models import Student as StudentModel

        daily_expected = 0
        daily_fee_types = FeeType.objects.filter(
            school=school,
            collection_frequency='DAILY',
            is_active=True,
        )
        for ft in daily_fee_types:
            for structure in FeeStructure.objects.filter(school=school, fee_type=ft):
                student_count = StudentModel.objects.filter(
                    current_class__school=school,
                    current_class__level=structure.level,
                    is_active=True,
                ).count()
                # Expected = amount per day × total school days in current term × student count
                current_term = school.current_term if hasattr(school, 'current_term') and school.current_term else None
                if not current_term and hasattr(school, 'current_term_id') and school.current_term_id:
                    from schools.models import Term as TermModel
                    try:
                        current_term = TermModel.objects.get(id=school.current_term_id)
                    except TermModel.DoesNotExist:
                        current_term = None
                term_days = current_term.total_days if current_term and current_term.total_days > 0 else 0
                daily_expected += float(structure.amount) * term_days * student_count

        # --- Non-daily (term/year) stats from TermBills ---
        # Keep these metrics on the same basis (TermBill) so collected % is coherent.
        non_daily_collected = TermBill.objects.filter(
            school=school,
        ).exclude(
            status='WAIVED',
        ).exclude(
            fee_type__collection_frequency='DAILY',
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        non_daily_outstanding = TermBill.objects.filter(
            school=school,
        ).exclude(
            status='WAIVED',
        ).exclude(
            fee_type__collection_frequency='DAILY',
        ).aggregate(total=Sum('balance'))['total'] or 0
        non_daily_outstanding = max(0, float(non_daily_outstanding))

        non_daily_payment_count = FeePayment.objects.filter(
            school=school,
        ).exclude(
            fee_type__collection_frequency='DAILY',
        ).count()

        # Legacy totals kept for backwards-compat
        total_billed = TermBill.objects.filter(
            school=school
        ).aggregate(Sum('amount_billed'))['amount_billed__sum'] or 0

        total_collected = FeePayment.objects.filter(
            school=school
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

        total_outstanding = TermBill.objects.filter(
            school=school
        ).exclude(status='WAIVED').aggregate(
            total=Sum('balance')
        )['total'] or 0
        total_outstanding = max(0, float(total_outstanding))

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

        total_payment_count = FeePayment.objects.filter(school=school).count()

        return Response({
            'total_billed': float(total_billed),
            'total_outstanding': total_outstanding,
            'total_collected': float(total_collected),
            'total_payment_count': total_payment_count,
            # New daily/non-daily breakdown
            'daily_collected': float(daily_collected),
            'daily_expected': float(daily_expected),
            'non_daily_collected': float(non_daily_collected),
            'non_daily_outstanding': float(non_daily_outstanding),
            'non_daily_payment_count': non_daily_payment_count,
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

    @action(detail=False, methods=['get'])
    def all_classes_summary(self, request):
        """
        Return every class in the school with daily-fee vs term/other-fee
        collection totals so the admin can compare across classes at a glance.

        Response shape:
        [
          {
            "class_id": 3,
            "class_name": "BS 9 A",
            "level": "BS_9",
            "section": "A",
            "total_students": 32,
            "daily_collected": 450.00,
            "term_collected": 12000.00,
            "total_collected": 12450.00
          },
          ...
        ]
        """
        school = request.user.school

        # All classes for this school ordered alphabetically
        classes = Class.objects.filter(school=school).order_by('level', 'section')

        # All payments for the school in one query, annotated with frequency
        # We join through fee_type to get collection_frequency
        payments_qs = FeePayment.objects.filter(school=school).select_related(
            'student__current_class', 'fee_type'
        )

        # Build a dict: class_id -> {daily: Decimal, term: Decimal}
        from decimal import Decimal
        from collections import defaultdict
        class_totals = defaultdict(lambda: {'daily': Decimal('0'), 'term': Decimal('0')})

        for payment in payments_qs:
            cls_obj = payment.student.current_class
            if cls_obj is None:
                continue
            freq = payment.fee_type.collection_frequency if payment.fee_type else 'TERM'
            bucket = 'daily' if freq == 'DAILY' else 'term'
            class_totals[cls_obj.id][bucket] += payment.amount_paid

        # Student counts per class
        student_counts = {
            row['current_class_id']: row['count']
            for row in Student.objects.filter(
                current_class__school=school
            ).values('current_class_id').annotate(count=Count('id'))
        }

        result = []
        for cls in classes:
            totals = class_totals.get(cls.id, {'daily': Decimal('0'), 'term': Decimal('0')})
            daily = float(totals['daily'])
            term = float(totals['term'])
            result.append({
                'class_id': cls.id,
                'class_name': cls.full_name if hasattr(cls, 'full_name') else f"{cls.level} {cls.section}".strip(),
                'level': cls.level,
                'section': cls.section,
                'total_students': student_counts.get(cls.id, 0),
                'daily_collected': daily,
                'term_collected': term,
                'total_collected': daily + term,
            })

        # Sort by total_collected descending
        result.sort(key=lambda x: x['total_collected'], reverse=True)
        return Response(result)


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

        # ── Update StudentFee.total_amount for all affected students ──────────
        # This keeps the "Student Fees" running-total tab accurate.
        if created_count > 0 or updated_count > 0:
            try:
                from decimal import Decimal as _Dec
                from django.db.models import Sum as _Sum
                for student in students:
                    total_billed = TermBill.objects.filter(
                        student=student, school=school
                    ).aggregate(t=_Sum('amount_billed'))['t'] or _Dec('0')
                    sf, _ = StudentFee.objects.get_or_create(
                        student=student,
                        school=school,
                        defaults={
                            'total_amount': total_billed,
                            'amount_paid': _Dec('0'),
                            'balance': total_billed,
                        },
                    )
                    if sf.pk:
                        sf.total_amount = total_billed
                        _bal = total_billed - sf.amount_paid
                        sf.balance = _bal if _bal > _Dec('0') else _Dec('0')
                        if sf.total_amount > 0 and sf.balance <= _Dec('0'):
                            sf.status = 'PAID'
                        elif sf.amount_paid > _Dec('0'):
                            sf.status = 'PARTIAL'
                        else:
                            sf.status = 'NOT_STARTED'
                        sf.save()
            except Exception as _sf_err:
                logger.warning(f'StudentFee sync after bill generate failed: {_sf_err}')

        # Send email notifications to guardians/parents for newly created bills
        if created_count > 0:
            try:
                from notifications.email_service import EmailService
                # Group new bills by student for a single email per student
                from collections import defaultdict
                student_bills = defaultdict(list)
                for bill in TermBill.objects.filter(
                    school=school, term=term
                ).select_related('student', 'fee_type'):
                    student_bills[bill.student_id].append(bill)
                for student_id, student_bill_list in student_bills.items():
                    try:
                        EmailService.send_bills_generated(
                            student_bill_list[0].student,
                            student_bill_list,
                            term,
                        )
                    except Exception:
                        pass
            except Exception:
                pass  # Email failure must never break bill generation

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

    @action(detail=False, methods=['get'], url_path='my-bills')
    def my_bills(self, request):
        """
        Student-facing: return the authenticated student's term bills
        plus their daily fee payments, grouped by term.

        Accessible by students and parents (parent sees child bills via
        ?student_id=<id> if they are linked).
        """
        role = getattr(request.user, 'role', '')
        school = request.user.school

        # --- resolve which student we are looking at ---
        if role == 'STUDENT':
            try:
                student = request.user.student_profile
            except Exception:
                return Response({'error': 'Student record not found'}, status=status.HTTP_404_NOT_FOUND)
        elif role == 'PARENT':
            from accounts.models import ParentStudent
            student_id = request.query_params.get('student_id')
            if not student_id:
                return Response({'error': 'student_id required for parent access'}, status=status.HTTP_400_BAD_REQUEST)
            # Verify child is linked to this parent
            linked_ids = list(
                ParentStudent.objects.filter(parent=request.user)
                .values_list('student__student_id', flat=True)
            )
            if student_id not in linked_ids:
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
            try:
                student = Student.objects.get(student_id=student_id, school=school)
            except Student.DoesNotExist:
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)

        # --- term bills (non-daily: TERM/YEAR fees) ---
        bills_qs = TermBill.objects.filter(
            student=student, school=school
        ).select_related('fee_type', 'term', 'term__academic_year').order_by(
            '-term__start_date', 'fee_type__name'
        )

        term_filter = request.query_params.get('term')
        if term_filter:
            bills_qs = bills_qs.filter(term_id=term_filter)

        bills_data = []
        for bill in bills_qs:
            bills_data.append({
                'id': bill.id,
                'fee_type': bill.fee_type.name,
                'fee_type_id': bill.fee_type_id,
                'collection_frequency': bill.fee_type.collection_frequency,
                'term': bill.term.get_name_display(),
                'term_id': bill.term_id,
                'academic_year': bill.term.academic_year.name,
                'amount_billed': float(bill.amount_billed),
                'amount_paid': float(bill.amount_paid),
                'balance': float(bill.balance),
                'status': bill.status,
                'due_date': str(bill.due_date) if bill.due_date else None,
            })

        # --- daily fee payments summary ---
        daily_payments = FeePayment.objects.filter(
            student=student,
            school=school,
            fee_type__collection_frequency='DAILY',
        ).select_related('fee_type').order_by('fee_type__name', '-attendance_date')

        if term_filter:
            # Daily payments don't have term FK; filter by date range of term
            try:
                from schools.models import Term as TermModel
                t = TermModel.objects.get(id=term_filter)
                daily_payments = daily_payments.filter(
                    attendance_date__gte=t.start_date,
                    attendance_date__lte=t.end_date,
                )
            except Exception:
                pass

        # Group by fee_type
        from collections import defaultdict
        daily_by_type: dict = defaultdict(lambda: {'total_paid': 0, 'days_paid': 0, 'payments': []})
        for p in daily_payments:
            key = p.fee_type.name
            daily_by_type[key]['fee_type_id'] = p.fee_type_id
            daily_by_type[key]['amount_per_day'] = float(p.amount_paid)  # last seen amount
            daily_by_type[key]['total_paid'] += float(p.amount_paid)
            daily_by_type[key]['days_paid'] += 1
            daily_by_type[key]['payments'].append({
                'date': str(p.attendance_date) if p.attendance_date else str(p.payment_date)[:10],
                'amount': float(p.amount_paid),
            })

        daily_data = [
            {
                'fee_type': name,
                'fee_type_id': v['fee_type_id'],
                'collection_frequency': 'DAILY',
                'days_paid': v['days_paid'],
                'amount_per_day': v.get('amount_per_day', 0),
                'total_paid': v['total_paid'],
                'recent_payments': v['payments'][:10],
            }
            for name, v in daily_by_type.items()
        ]

        # --- totals ---
        total_billed = sum(b['amount_billed'] for b in bills_data)
        total_paid_bills = sum(b['amount_paid'] for b in bills_data)
        total_balance = sum(b['balance'] for b in bills_data)
        total_daily_paid = sum(d['total_paid'] for d in daily_data)

        return Response({
            'student': {
                'id': student.id,
                'name': f"{student.user.first_name} {student.user.last_name}",
                'student_id': student.student_id,
                'class': str(student.current_class) if student.current_class else '',
            },
            'term_bills': bills_data,
            'daily_fees': daily_data,
            'summary': {
                'total_billed': total_billed,
                'total_paid_bills': total_paid_bills,
                'total_balance': total_balance,
                'total_daily_paid': total_daily_paid,
                'grand_total_paid': total_paid_bills + total_daily_paid,
            },
            'online_payments_enabled': school.parent_can_pay_fees_online if hasattr(school, 'parent_can_pay_fees_online') else False,
            'paystack_public_key': getattr(django_settings, 'PAYSTACK_PUBLIC_KEY', '') if getattr(school, 'parent_can_pay_fees_online', False) else None,
        })

    @action(detail=True, methods=['post'], url_path='initiate-paystack')
    def initiate_paystack(self, request, pk=None):
        """
        POST /fees/term-bills/<id>/initiate-paystack/
        Initiate a Paystack payment for a specific term bill.
        Accessible by STUDENT and PARENT only.
        Returns: { authorization_url, reference, amount, public_key }
        """
        import uuid
        import requests as http_requests

        role = getattr(request.user, 'role', '')
        school = request.user.school

        # Resolve student
        if role == 'STUDENT':
            try:
                student = request.user.student_profile
            except Exception:
                return Response({'error': 'Student record not found'}, status=status.HTTP_404_NOT_FOUND)
        elif role == 'PARENT':
            from accounts.models import ParentStudent
            student_id = request.data.get('student_id') or request.query_params.get('student_id')
            if not student_id:
                return Response({'error': 'student_id required'}, status=status.HTTP_400_BAD_REQUEST)
            linked_ids = list(ParentStudent.objects.filter(parent=request.user).values_list('student__student_id', flat=True))
            if student_id not in linked_ids:
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
            try:
                student = Student.objects.get(student_id=student_id, school=school)
            except Student.DoesNotExist:
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)

        # Check online payments enabled
        secret_key = getattr(django_settings, 'PAYSTACK_SECRET_KEY', '')
        public_key = getattr(django_settings, 'PAYSTACK_PUBLIC_KEY', '')
        if not getattr(school, 'parent_can_pay_fees_online', False):
            return Response({'error': 'Online payments are not enabled for this school.'}, status=status.HTTP_400_BAD_REQUEST)
        if not secret_key:
            return Response({'error': 'Payment gateway not configured.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the bill — must belong to this student + school
        try:
            bill = TermBill.objects.get(pk=pk, student=student, school=school)
        except TermBill.DoesNotExist:
            return Response({'error': 'Bill not found.'}, status=status.HTTP_404_NOT_FOUND)

        if bill.status in ('PAID', 'WAIVED'):
            return Response({'error': 'This bill is already paid or waived.'}, status=status.HTTP_400_BAD_REQUEST)

        amount_to_pay = float(bill.balance)
        if amount_to_pay <= 0:
            return Response({'error': 'No outstanding balance.'}, status=status.HTTP_400_BAD_REQUEST)

        # Paystack expects amount in smallest currency unit (kobo for NGN, pesewas for GHS)
        amount_smallest = int(amount_to_pay * 100)

        payer_email = request.user.email or ''
        if not payer_email:
            return Response({'error': 'User email required for payment.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"FEE-{bill.id}-{uuid.uuid4().hex[:8].upper()}"

        paystack_url = 'https://api.paystack.co/transaction/initialize'
        headers = {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'email': payer_email,
            'amount': amount_smallest,
            'reference': reference,
            'metadata': {
                'bill_id': bill.id,
                'student_id': student.student_id,
                'fee_type': bill.fee_type.name,
                'school_id': school.id,
            },
            'callback_url': f"{getattr(django_settings, 'FRONTEND_URL', '')}/student/bills?paystack_ref={reference}",
        }

        try:
            resp = http_requests.post(paystack_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Paystack initiate error: {e}")
            return Response({'error': 'Payment gateway error. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        if not data.get('status'):
            return Response({'error': data.get('message', 'Payment initiation failed.')}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'authorization_url': data['data']['authorization_url'],
            'reference': reference,
            'amount': amount_to_pay,
            'public_key': public_key,
        })

    @action(detail=False, methods=['get'], url_path='verify-paystack')
    def verify_paystack(self, request):
        """
        GET /fees/term-bills/verify-paystack/?reference=<ref>
        Verify a Paystack payment and record it if successful.
        Accessible by STUDENT and PARENT.
        """
        import requests as http_requests
        from decimal import Decimal

        reference = request.query_params.get('reference', '').strip()
        if not reference:
            return Response({'error': 'reference is required'}, status=status.HTTP_400_BAD_REQUEST)

        role = getattr(request.user, 'role', '')
        school = request.user.school

        if role not in ('STUDENT', 'PARENT'):
            return Response({'error': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)

        secret_key = getattr(django_settings, 'PAYSTACK_SECRET_KEY', '')
        if not secret_key:
            return Response({'error': 'Payment gateway not configured.'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract bill_id from reference format: FEE-<id>-<hex>
        try:
            bill_id = int(reference.split('-')[1])
        except (IndexError, ValueError):
            return Response({'error': 'Invalid reference format.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bill = TermBill.objects.get(pk=bill_id, school=school)
        except TermBill.DoesNotExist:
            return Response({'error': 'Bill not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency: already recorded
        if FeePayment.objects.filter(paystack_reference=reference, paystack_status='success').exists():
            return Response({'already_recorded': True, 'bill_status': bill.status})

        # Verify with Paystack
        verify_url = f'https://api.paystack.co/transaction/verify/{reference}'
        headers = {'Authorization': f'Bearer {secret_key}'}
        try:
            resp = http_requests.get(verify_url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Paystack verify error: {e}")
            return Response({'error': 'Payment verification failed. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        if not data.get('status') or data['data'].get('status') != 'success':
            return Response({'success': False, 'message': 'Payment not successful.'})

        amount_paid_smallest = data['data']['amount']
        amount_paid = Decimal(str(amount_paid_smallest)) / 100

        # Record the payment
        FeePayment.objects.create(
            student=bill.student,
            school=school,
            fee_type=bill.fee_type,
            amount_paid=amount_paid,
            payment_method='PAYSTACK',
            reference_number=reference,
            paystack_reference=reference,
            paystack_status='success',
            is_verified=True,
            notes=f'Online payment via Paystack. Ref: {reference}',
        )

        # Update TermBill amount_paid (balance is computed by the model's save())
        bill.amount_paid = Decimal(str(bill.amount_paid)) + amount_paid
        bill.save()

        # Update running StudentFee totals so the Student Fees tab stays accurate
        try:
            sf, _ = StudentFee.objects.get_or_create(
                student=bill.student,
                school=school,
                defaults={
                    'total_amount': Decimal('0'),
                    'amount_paid': Decimal('0'),
                    'balance': Decimal('0'),
                },
            )
            sf.amount_paid += amount_paid
            _bal = sf.total_amount - sf.amount_paid
            sf.balance = _bal if _bal > Decimal('0') else Decimal('0')
            from django.utils import timezone as _tz
            sf.last_payment_date = _tz.now()
            if sf.total_amount > 0 and sf.balance <= Decimal('0'):
                sf.status = 'PAID'
            elif sf.amount_paid > Decimal('0'):
                sf.status = 'PARTIAL'
            sf.save()
        except Exception as _sf_err:
            logger.warning(f'StudentFee sync after Paystack verify failed: {_sf_err}')

        return Response({
            'success': True,
            'amount_paid': float(amount_paid),
            'bill_status': bill.status,
            'reference': reference,
        })

    @action(detail=False, methods=['post'], url_path='send-fee-reminders')
    def send_fee_reminders(self, request):
        """
        POST /fees/term-bills/send-fee-reminders/
        Send SMS + in-app notification to parents/guardians of students
        with UNPAID or PARTIAL bills.

        Body (all optional):
          {
            "term": <id>,           // filter to a specific term
            "class_id": <id>,       // filter to a class
            "fee_type": <id>,       // filter to a specific fee type
            "message": "...",       // custom SMS message (uses default if omitted)
            "dry_run": false        // if true, return who would be notified without sending
          }

        Returns: { sent: N, skipped: N, no_phone: N, details: [...] }
        """
        from notifications.sms_service import SmsService
        from notifications.models import Notification

        role = getattr(request.user, 'role', '')
        if role not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response({'error': 'Only admins can send fee reminders.'}, status=status.HTTP_403_FORBIDDEN)

        school = request.user.school
        if not getattr(school, 'sms_enabled', False):
            return Response({'error': 'SMS is not enabled for this school. Enable it in School Settings.'}, status=status.HTTP_400_BAD_REQUEST)
        if not getattr(school, 'sms_fee_reminder_enabled', False):
            return Response({'error': 'SMS fee reminders are not enabled. Enable "SMS Fee Reminders" in School Settings.'}, status=status.HTTP_400_BAD_REQUEST)

        dry_run = request.data.get('dry_run', False)
        custom_message = request.data.get('message', '').strip()

        # Pre-flight: check SMS balance and API key before doing any work
        if not dry_run:
            from notifications.sms_service import SmsService as _Svc
            api_key = _Svc._get_api_key(school)
            if not api_key:
                return Response(
                    {'error': 'Arkesel API key is not configured. Contact your system administrator.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            sms_balance = getattr(school, 'sms_balance', 0)
            if sms_balance < 1:
                return Response(
                    {'error': f'Insufficient SMS credits (balance: {sms_balance}). Please top up in SMS Settings.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # statuses filter — defaults to outstanding (UNPAID + PARTIAL)
        allowed = {'UNPAID', 'PARTIAL', 'PAID', 'WAIVED'}
        requested_statuses = request.data.get('statuses', ['UNPAID', 'PARTIAL'])
        if not isinstance(requested_statuses, list):
            requested_statuses = ['UNPAID', 'PARTIAL']
        statuses = [s for s in requested_statuses if s in allowed] or ['UNPAID', 'PARTIAL']

        # Build queryset of bills matching the requested statuses
        qs = TermBill.objects.filter(
            school=school,
            status__in=statuses,
        ).select_related('student', 'fee_type', 'term')

        term_id = request.data.get('term')
        if term_id:
            qs = qs.filter(term_id=term_id)

        class_id = request.data.get('class_id')
        if class_id:
            qs = qs.filter(student__current_class_id=class_id)

        fee_type_id = request.data.get('fee_type')
        if fee_type_id:
            qs = qs.filter(fee_type_id=fee_type_id)

        # Group bills by student so one student gets one SMS
        from collections import defaultdict
        student_bills: dict = defaultdict(list)
        for bill in qs:
            student_bills[bill.student_id].append(bill)

        sent = 0
        skipped = 0
        no_phone = 0
        details = []

        for student_id, bills in student_bills.items():
            student = bills[0].student
            phone = getattr(student, 'guardian_phone', '') or ''
            total_billed = sum(float(b.amount_billed) for b in bills)
            total_paid = sum(float(b.amount_paid) for b in bills)
            total_balance = sum(float(b.balance) for b in bills)

            if custom_message:
                sms_text = custom_message.replace('{student}', student.get_full_name()).replace('{balance}', f'GH\u20b5{total_balance:,.2f}')
            else:
                guardian = getattr(student, 'guardian_name', '') or 'Guardian'
                student_name = student.get_full_name()
                school_name = school.name

                # Build per-fee breakdown: "Tuition: Billed GH₵500 | Paid GH₵200 | Arrears GH₵300"
                fee_lines = []
                for b in bills:
                    billed = float(b.amount_billed)
                    paid = float(b.amount_paid)
                    arrears = float(b.balance)
                    fee_lines.append(
                        f'{b.fee_type.name}: Billed GH\u20b5{billed:,.2f} | Paid GH\u20b5{paid:,.2f} | Arrears GH\u20b5{arrears:,.2f}'
                    )
                breakdown = ' | '.join(fee_lines)

                sms_text = (
                    f'Dear {guardian}, this is a fee reminder from {school_name}.\n'
                    f'Student: {student_name}\n'
                    f'{breakdown}\n'
                    f'Total Arrears: GH\u20b5{total_balance:,.2f}\n'
                    f'Please visit the school to settle outstanding fees. Thank you.'
                )
                # Trim to 320 chars (2 SMS segments) to stay cost-effective
                if len(sms_text) > 320:
                    sms_text = sms_text[:317] + '...'

            detail = {
                'student': student.get_full_name(),
                'student_id': student.student_id,
                'guardian_phone': phone if phone else None,
                'total_billed': total_billed,
                'total_paid': total_paid,
                'total_balance': total_balance,
                'bills': [
                    {
                        'fee_type': b.fee_type.name,
                        'amount_billed': float(b.amount_billed),
                        'amount_paid': float(b.amount_paid),
                        'balance': float(b.balance),
                        'status': b.status,
                    }
                    for b in bills
                ],
            }

            if not phone:
                no_phone += 1
                detail['result'] = 'no_phone'
                details.append(detail)
                continue

            if dry_run:
                detail['result'] = 'would_send'
                detail['message_preview'] = sms_text
                details.append(detail)
                sent += 1
                continue

            # Send SMS
            success = SmsService.send([phone], sms_text, school)
            if success:
                sent += 1
                detail['result'] = 'sent'
            else:
                skipped += 1
                detail['result'] = 'failed'
                # Capture the likely reason for the failure
                current_bal = getattr(school, 'sms_balance', 0)
                if current_bal < 1:
                    detail['failure_reason'] = 'insufficient_balance'
                else:
                    detail['failure_reason'] = 'api_error'

            # Also send in-app notification to linked parent user accounts
            try:
                from accounts.models import ParentStudent
                parent_users = [ps.parent for ps in ParentStudent.objects.filter(student=student).select_related('parent')]
                for parent in parent_users:
                    Notification.objects.create(
                        user=parent,
                        title='📢 Fee Payment Reminder',
                        message=f'Outstanding balance for {student.get_full_name()}: GH₵{total_balance:,.2f}. Please clear fees as soon as possible.',
                        type='warning',
                    )
                # Also notify the student's own user account if it exists
                if hasattr(student, 'user') and student.user:
                    Notification.objects.create(
                        user=student.user,
                        title='📢 Fee Payment Reminder',
                        message=f'You have outstanding fees of GH₵{total_balance:,.2f}. Please ask your guardian to pay at the school.',
                        type='warning',
                    )
            except Exception as notif_err:
                logger.warning(f'In-app notification failed for student {student_id}: {notif_err}')

            details.append(detail)

        # Surface a clear failure_reason if nothing sent
        failure_reason = None
        if not dry_run and sent == 0 and skipped > 0:
            reasons = {d.get('failure_reason') for d in details if d.get('failure_reason')}
            if 'insufficient_balance' in reasons:
                failure_reason = f'insufficient SMS credits (balance: {getattr(school, "sms_balance", 0)})'
            elif 'api_error' in reasons:
                failure_reason = 'SMS provider rejected the request — check API configuration'

        # Persist SMS log (skip for dry runs)
        if not dry_run:
            try:
                from notifications.models import SmsLog
                if sent > 0 and skipped == 0:
                    log_status = 'success'
                elif sent > 0 and skipped > 0:
                    log_status = 'partial'
                elif sent == 0 and skipped > 0:
                    log_status = 'failed'
                else:
                    log_status = 'success'  # all had no-phone, nothing to send

                # Build filters snapshot
                filters_snapshot = {'statuses': statuses}
                if class_id:
                    filters_snapshot['class_id'] = class_id
                if fee_type_id:
                    filters_snapshot['fee_type_id'] = fee_type_id
                if term_id:
                    filters_snapshot['term_id'] = term_id

                # First 200 chars of the message used
                sample_msg = ''
                for d in details:
                    if d.get('message_preview'):
                        sample_msg = d['message_preview'][:200]
                        break

                SmsLog.objects.create(
                    school=school,
                    sent_by=request.user,
                    sms_type='fee_reminder',
                    status=log_status,
                    total_recipients=len(student_bills),
                    sent_count=sent,
                    failed_count=skipped,
                    no_phone_count=no_phone,
                    message_preview=sample_msg or (custom_message[:200] if custom_message else ''),
                    filters_used=filters_snapshot,
                    details=details,
                    failure_reason=failure_reason or '',
                )
            except Exception as log_err:
                logger.warning(f'Failed to write SmsLog: {log_err}')

        # Re-read the final balance from DB to return to the client
        try:
            from schools.models import School as _SchoolModel
            _fresh = _SchoolModel.objects.filter(pk=school.pk).values('sms_balance').first()
            sms_balance_remaining = _fresh['sms_balance'] if _fresh else getattr(school, 'sms_balance', 0)
        except Exception:
            sms_balance_remaining = getattr(school, 'sms_balance', 0)

        return Response({
            'dry_run': dry_run,
            'sent': sent,
            'skipped': skipped,
            'no_phone': no_phone,
            'total_students': len(student_bills),
            'failure_reason': failure_reason,
            'sms_balance_remaining': sms_balance_remaining,
            'details': details,
        })
