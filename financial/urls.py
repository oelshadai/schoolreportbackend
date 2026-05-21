from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffViewSet, StaffSalaryViewSet, PayrollRecordViewSet,
    IncomeViewSet, ExpenseViewSet, BudgetViewSet,
    BudgetItemViewSet, FinancialAuditLogViewSet, FinancialDashboardView
)

router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'salaries', StaffSalaryViewSet, basename='salary')
router.register(r'payroll', PayrollRecordViewSet, basename='payroll')
router.register(r'income', IncomeViewSet, basename='income')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'budget-items', BudgetItemViewSet, basename='budget-item')
router.register(r'audit-logs', FinancialAuditLogViewSet, basename='audit-log')
router.register(r'dashboard', FinancialDashboardView, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
