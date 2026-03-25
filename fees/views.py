from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Sum, Count
from .models import FeeType, FeeStructure, StudentFee, FeePayment, FeeCollection
from .serializers import (
    FeeTypeSerializer, FeeStructureSerializer, StudentFeeSerializer,
    FeePaymentSerializer, FeePaymentCreateSerializer, FeeCollectionSerializer,
    StudentSearchSerializer, FeeCollectionReportSerializer
)
from students.models import Student
from schools.models import Class
import logging

logger = logging.getLogger(__name__)


class FeeTypeViewSet(viewsets.ModelViewSet):
    """Manage fee types"""
    serializer_class = FeeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FeeType.objects.filter(school=self.request.user.school, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


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
        """Collect fee from student"""
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
