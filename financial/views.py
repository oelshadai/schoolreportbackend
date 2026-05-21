from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from calendar import month_name

# Import models from schools app
from schools.models import (
    Staff, StaffSalary, PayrollRecord, Income, Expense,
    Budget, BudgetItem, ExpenseApproval, PaymentReminder, FinancialAuditLog
)
from schools.signals import set_audit_context, clear_audit_context
from .serializers import (
    StaffSerializer, StaffSalarySerializer, PayrollRecordSerializer,
    IncomeSerializer, ExpenseSerializer, BudgetSerializer,
    BudgetItemSerializer, ExpenseApprovalSerializer, PaymentReminderSerializer,
    FinancialAuditLogSerializer
)


class StaffViewSet(viewsets.ModelViewSet):
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Staff.objects.filter(school=user.school)
        return Staff.objects.none()
    
    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save(school=self.request.user.school)
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()


class StaffSalaryViewSet(viewsets.ModelViewSet):
    serializer_class = StaffSalarySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return StaffSalary.objects.filter(staff__school=user.school)
        return StaffSalary.objects.none()

    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()


class PayrollRecordViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return PayrollRecord.objects.filter(school=user.school)
        return PayrollRecord.objects.none()
    
    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save(
                school=self.request.user.school,
                created_by=self.request.user
            )
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()
    
    @action(detail=False, methods=['post'])
    def generate_monthly(self, request):
        """Generate payroll for all active staff for a given month"""
        set_audit_context(request.user, action='GENERATE', notes='Batch payroll generation')
        try:
            month = request.data.get('month')
            year = request.data.get('year')

            if not month or not year:
                return Response(
                    {'error': 'Month and year are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            school = request.user.school
            active_staff = Staff.objects.filter(school=school, status='ACTIVE')

            created_count = 0
            skipped_count = 0

            for staff in active_staff:
                # Check if payroll already exists
                if PayrollRecord.objects.filter(
                    school=school, staff=staff, month=month, year=year
                ).exists():
                    skipped_count += 1
                    continue

                # Get active salary
                salary = StaffSalary.objects.filter(
                    staff=staff, is_active=True
                ).first()

                if not salary:
                    skipped_count += 1
                    continue

                # Create payroll record
                PayrollRecord.objects.create(
                    school=school,
                    staff=staff,
                    salary=salary,
                    month=month,
                    year=year,
                    basic_salary=salary.basic_salary,
                    allowances=salary.housing_allowance + salary.transport_allowance + salary.other_allowances,
                    deductions=salary.tax_deduction + salary.pension_deduction + salary.other_deductions,
                    gross_salary=salary.gross_salary(),
                    net_salary=salary.net_salary(),
                    created_by=request.user
                )
                created_count += 1

            return Response({
                'message': f'Payroll generated successfully',
                'created': created_count,
                'skipped': skipped_count
            })
        finally:
            clear_audit_context()
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark payroll as paid"""
        set_audit_context(request.user, action='PAY', extra_data={
            'payment_reference': request.data.get('payment_reference', '')
        })
        try:
            payroll = self.get_object()
            payroll.status = 'PAID'
            payroll.payment_date = request.data.get('payment_date', timezone.now().date())
            payroll.payment_method = request.data.get('payment_method', '')
            payroll.payment_reference = request.data.get('payment_reference', '')
            payroll.save()
            return Response({'message': 'Payroll marked as paid'})
        finally:
            clear_audit_context()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve payroll"""
        set_audit_context(request.user, action='APPROVE')
        try:
            payroll = self.get_object()
            payroll.status = 'APPROVED'
            payroll.approved_by = request.user
            payroll.save()
            return Response({'message': 'Payroll approved'})
        finally:
            clear_audit_context()


class IncomeViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Income.objects.filter(school=user.school)
        return Income.objects.none()
    
    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save(
                school=self.request.user.school,
                recorded_by=self.request.user
            )
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Expense.objects.filter(school=user.school)
        return Expense.objects.none()
    
    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save(
                school=self.request.user.school,
                requested_by=self.request.user
            )
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve expense"""
        set_audit_context(request.user, action='APPROVE', notes=request.data.get('comments', ''))
        try:
            expense = self.get_object()
            expense.status = 'APPROVED'
            expense.approved_by = request.user
            expense.save()
            
            # Create approval record
            ExpenseApproval.objects.create(
                expense=expense,
                approver=request.user,
                status='APPROVED',
                comments=request.data.get('comments', '')
            )
            
            return Response({'message': 'Expense approved'})
        finally:
            clear_audit_context()
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject expense"""
        set_audit_context(request.user, action='REJECT', notes=request.data.get('comments', ''))
        try:
            expense = self.get_object()
            expense.status = 'REJECTED'
            expense.save()
            
            # Create approval record
            ExpenseApproval.objects.create(
                expense=expense,
                approver=request.user,
                status='REJECTED',
                comments=request.data.get('comments', '')
            )
            
            return Response({'message': 'Expense rejected'})
        finally:
            clear_audit_context()


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return Budget.objects.filter(school=user.school)
        return Budget.objects.none()
    
    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save(
                school=self.request.user.school,
                created_by=self.request.user
            )
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()


class BudgetItemViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            return BudgetItem.objects.filter(budget__school=user.school)
        return BudgetItem.objects.none()

    def perform_create(self, serializer):
        set_audit_context(self.request.user, action='CREATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def perform_update(self, serializer):
        set_audit_context(self.request.user, action='UPDATE')
        try:
            serializer.save()
        finally:
            clear_audit_context()

    def destroy(self, request, *args, **kwargs):
        set_audit_context(request.user, action='DELETE')
        try:
            return super().destroy(request, *args, **kwargs)
        finally:
            clear_audit_context()


class FinancialAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FinancialAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.school:
            return FinancialAuditLog.objects.filter(school=user.school)
        return FinancialAuditLog.objects.none()


class FinancialDashboardView(viewsets.ViewSet):
    """Financial dashboard with analytics and charts data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        try:
            school = request.user.school
        except Exception as e:
            print(f"Error getting school: {e}")
            import traceback
            print(traceback.format_exc())
            return Response({'error': f'Error getting school: {str(e)}'}, status=400)
        
        if not school:
            return Response({'error': 'No school associated'}, status=400)
        
        try:
            # Date filters
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            
            # Total income
            total_income = Income.objects.filter(school=school).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # Total expenses (only approved/paid)
            total_expenses = Expense.objects.filter(
                school=school,
                status__in=['APPROVED', 'PAID']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Monthly income
            monthly_income = Income.objects.filter(
                school=school,
                date__gte=current_month_start
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Monthly expenses
            monthly_expenses = Expense.objects.filter(
                school=school,
                status__in=['APPROVED', 'PAID'],
                date__gte=current_month_start
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Payroll summary
            total_payroll = PayrollRecord.objects.filter(
                school=school
            ).aggregate(total=Sum('net_salary'))['total'] or Decimal('0')
            
            pending_payroll = PayrollRecord.objects.filter(
                school=school,
                status__in=['DRAFT', 'APPROVED']
            ).aggregate(total=Sum('net_salary'))['total'] or Decimal('0')
            
            # Staff count
            active_staff = Staff.objects.filter(school=school, status='ACTIVE').count()
            
            # Pending approvals
            pending_expenses = Expense.objects.filter(
                school=school,
                status='PENDING'
            ).count()
            
            # Budget utilization
            budget_utilization = 0
            try:
                active_budgets = Budget.objects.filter(
                    school=school,
                    is_active=True
                )
                
                if active_budgets.exists():
                    total_budget = active_budgets.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                    # Calculate utilized from budget items
                    total_utilized = BudgetItem.objects.filter(
                        budget__in=active_budgets
                    ).aggregate(total=Sum('spent_amount'))['total'] or Decimal('0')
                    budget_utilization = float((total_utilized / total_budget * 100) if total_budget > 0 else 0)
            except Exception as e:
                print(f"Budget calculation error: {e}")
                budget_utilization = 0
            
            # Monthly trend (last 6 months)
            monthly_trend = []
            try:
                for i in range(5, -1, -1):
                    month_date = today - timedelta(days=30 * i)
                    month_start = month_date.replace(day=1)
                    
                    if i == 0:
                        month_end = today
                    else:
                        next_month = month_start.replace(day=28) + timedelta(days=4)
                        month_end = next_month - timedelta(days=next_month.day)
                    
                    month_income = Income.objects.filter(
                        school=school,
                        date__gte=month_start,
                        date__lte=month_end
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    
                    month_expenses = Expense.objects.filter(
                        school=school,
                        status__in=['APPROVED', 'PAID'],
                        date__gte=month_start,
                        date__lte=month_end
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    
                    monthly_trend.append({
                        'month': month_name[month_start.month][:3],
                        'income': float(month_income),
                        'expenses': float(month_expenses),
                        'net': float(month_income - month_expenses)
                    })
            except Exception as e:
                print(f"Monthly trend error: {e}")
                monthly_trend = []
            
            # Income by category
            income_by_category = []
            try:
                income_categories = Income.objects.filter(
                    school=school
                ).values('category').annotate(
                    total=Sum('amount')
                ).order_by('-total')
                
                for item in income_categories:
                    income_by_category.append({
                        'category': item['category'],
                        'amount': float(item['total'])
                    })
            except Exception as e:
                print(f"Income category error: {e}")
                income_by_category = []
            
            # Expense by category
            expense_by_category = []
            try:
                expense_categories = Expense.objects.filter(
                    school=school,
                    status__in=['APPROVED', 'PAID']
                ).values('category').annotate(
                    total=Sum('amount')
                ).order_by('-total')
                
                for item in expense_categories:
                    expense_by_category.append({
                        'category': item['category'],
                        'amount': float(item['total'])
                    })
            except Exception as e:
                print(f"Expense category error: {e}")
                expense_by_category = []
            
            return Response({
                'total_income': float(total_income),
                'total_expenses': float(total_expenses),
                'net_balance': float(total_income - total_expenses),
                'monthly_summary': {
                    'income': float(monthly_income),
                    'expenses': float(monthly_expenses),
                    'net': float(monthly_income - monthly_expenses)
                },
                'payroll_summary': {
                    'total_staff': active_staff,
                    'total_payroll': float(total_payroll),
                    'pending_payroll': float(pending_payroll)
                },
                'pending_approvals': pending_expenses,
                'budget_utilization': budget_utilization,
                'monthly_trend': monthly_trend,
                'income_by_category': income_by_category,
                'expense_by_category': expense_by_category,
                'cash_flow': monthly_trend  # Same as monthly_trend for now
            })
        except Exception as e:
            import traceback
            print(f"Dashboard error: {e}")
            print(traceback.format_exc())
            return Response({
                'error': str(e),
                'total_income': 0,
                'total_expenses': 0,
                'net_balance': 0,
                'monthly_summary': {'income': 0, 'expenses': 0, 'net': 0},
                'payroll_summary': {'total_staff': 0, 'total_payroll': 0, 'pending_payroll': 0},
                'pending_approvals': 0,
                'budget_utilization': 0,
                'monthly_trend': [],
                'income_by_category': [],
                'expense_by_category': [],
                'cash_flow': []
            }, status=500)
